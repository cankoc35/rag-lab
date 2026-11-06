"""Validate source definitions and explicitly download one immutable snapshot.

The current manifest supports versioned official PostgreSQL HTML sources.
load_sources() is offline; only download_source() performs network/file writes.
"""

from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
from http.client import HTTPException
import json
import math
from pathlib import Path
import re
import shutil
from tempfile import mkdtemp
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from rag_workflow_lab.contracts import SourceSelection, SourceSnapshot, SourceSpec


class SourceManifestError(ValueError):
    """The source manifest cannot be read or contains an invalid definition."""


class SourceDownloadError(RuntimeError):
    """A source could not be downloaded or saved as a complete snapshot."""


class _NoRedirects(HTTPRedirectHandler):
    """Keep an explicit source request within its exact allowlisted URL."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _object(value: object, context: str) -> dict:
    if not isinstance(value, dict):
        raise SourceManifestError(f"{context} must be a JSON object.")
    return value


def _text(record: dict, key: str, context: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise SourceManifestError(
            f"{context}.{key} must be a non-empty string without surrounding whitespace."
        )
    return value


def _selection(value: object, context: str) -> SourceSelection:
    record = _object(value, context)
    mode = _text(record, "mode", context)
    if mode == "page":
        if "section_ids" in record:
            raise SourceManifestError(f"{context}: page mode must not define section_ids.")
        return SourceSelection(mode="page")
    if mode != "sections":
        raise SourceManifestError(f"{context}.mode must be 'page' or 'sections'.")

    section_ids = record.get("section_ids")
    if not isinstance(section_ids, list) or not section_ids:
        raise SourceManifestError(f"{context}.section_ids must be a non-empty list.")
    for index, section_id in enumerate(section_ids):
        if not isinstance(section_id, str) or not section_id or any(
            char.isspace() for char in section_id
        ):
            raise SourceManifestError(
                f"{context}.section_ids[{index}] must be a non-empty HTML ID without whitespace."
            )
    if len(section_ids) != len(set(section_ids)):
        raise SourceManifestError(f"{context}.section_ids contains duplicate IDs.")
    return SourceSelection(mode="sections", section_ids=tuple(section_ids))


def _source(value: object, index: int) -> SourceSpec:
    context = f"sources[{index}]"
    record = _object(value, context)
    source_id = _text(record, "source_id", context)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", source_id):
        raise SourceManifestError(
            f"{context}.source_id must use letters, digits, underscores or hyphens."
        )
    title = _text(record, "title", context)
    source_format = _text(record, "format", context)
    if source_format != "html":
        raise SourceManifestError(f"{context}.format must be 'html' for this manifest version.")
    version = _text(record, "postgresql_version", context)
    if not re.fullmatch(r"[1-9][0-9]*", version):
        raise SourceManifestError(f"{context}.postgresql_version must be a major version such as '18'.")

    url = _text(record, "url", context)
    try:
        parsed = urlsplit(url)
    except ValueError as exc:
        raise SourceManifestError(f"{context}.url is not a valid URL.") from exc
    if (
        parsed.scheme != "https"
        or parsed.netloc != "www.postgresql.org"
        or not re.fullmatch(rf"/docs/{re.escape(version)}/[A-Za-z0-9_-]+\.html", parsed.path)
        or parsed.query
        or parsed.fragment
        or url != parsed.geturl()
        or any(char.isspace() for char in url)
    ):
        raise SourceManifestError(
            f"{context}.url must be a canonical official HTTPS PostgreSQL {version} HTML URL "
            "without a query or fragment; use selection for section scope."
        )

    return SourceSpec(
        source_id=source_id,
        title=title,
        url=url,
        format="html",
        postgresql_version=version,
        selection=_selection(record.get("selection"), f"{context}.selection"),
    )


def load_sources(manifest_path: str | Path) -> list[SourceSpec]:
    """Read a selected schema-v1 manifest and return its sources in file order.

    Validate local data only: no HTTP requests, model calls or file writes.
    Raise SourceManifestError for unreadable files or invalid source records.
    """
    path = Path(manifest_path)
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise SourceManifestError(f"Cannot read source manifest '{path}': {exc}") from exc
    try:
        document = json.loads(content)
    except json.JSONDecodeError as exc:
        raise SourceManifestError(
            f"Invalid JSON in '{path}' at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc

    manifest = _object(document, "manifest")
    schema_version = manifest.get("schema_version")
    if type(schema_version) is not int or schema_version != 1:
        raise SourceManifestError("manifest.schema_version must be the integer 1.")
    if manifest.get("status") != "selected":
        raise SourceManifestError("manifest.status must be 'selected' before loading sources.")
    records = manifest.get("sources")
    if not isinstance(records, list) or not records:
        raise SourceManifestError("manifest.sources must be a non-empty list.")

    sources: list[SourceSpec] = []
    seen_ids: set[str] = set()
    seen_urls: set[str] = set()
    for index, record in enumerate(records):
        source = _source(record, index)
        if source.source_id in seen_ids:
            raise SourceManifestError(f"sources[{index}]: duplicate source_id '{source.source_id}'.")
        if source.url in seen_urls:
            raise SourceManifestError(f"sources[{index}]: duplicate URL '{source.url}'.")
        seen_ids.add(source.source_id)
        seen_urls.add(source.url)
        sources.append(source)
    return sources


def download_source(
    source: SourceSpec,
    output_dir: str | Path,
    *,
    timeout: float = 30.0,
) -> SourceSnapshot:
    """Fetch one source's raw HTML and write a new snapshot plus manifest.json.

    Each successful call creates a unique directory under output_dir. Existing
    snapshots and the input source manifest are never overwritten. Selection
    metadata is preserved; HTML section extraction belongs to the parser.
    """
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not math.isfinite(timeout)
        or timeout <= 0
    ):
        raise ValueError("timeout must be a finite positive number of seconds.")

    # Reuse the same source validation for callers constructing SourceSpec directly.
    source_data = asdict(source)
    if source.selection.mode == "page" and not source.selection.section_ids:
        source_data["selection"].pop("section_ids")
    else:
        source_data["selection"]["section_ids"] = list(source.selection.section_ids)
    source = _source(source_data, 0)

    request = Request(source.url, headers={
        "User-Agent": "RAG-Workflow-Lab/0.1",
        "Accept": "text/html, application/xhtml+xml",
        "Accept-Encoding": "identity",
    })
    try:
        with build_opener(_NoRedirects()).open(request, timeout=timeout) as response:
            status = response.status
            if status != 200:
                raise SourceDownloadError(f"{source.source_id}: expected HTTP 200, received {status}.")
            resolved_url = response.geturl()
            if resolved_url != source.url:
                raise SourceDownloadError(f"{source.source_id}: response URL differs from the selected URL.")
            content_type = response.headers.get_content_type()
            if content_type not in {"text/html", "application/xhtml+xml"}:
                raise SourceDownloadError(f"{source.source_id}: expected HTML, received {content_type}.")
            if response.headers.get("Content-Encoding", "identity").lower() not in {"", "identity"}:
                raise SourceDownloadError(f"{source.source_id}: unsupported compressed response.")
            charset = response.headers.get_content_charset()
            content = response.read()
    except HTTPError as exc:
        exc.close()
        raise SourceDownloadError(
            f"{source.source_id}: HTTP {exc.code} for {source.url}; redirects are not followed."
        ) from exc
    except (URLError, TimeoutError, HTTPException, OSError) as exc:
        raise SourceDownloadError(f"{source.source_id}: download failed for {source.url}: {exc}") from exc
    if not content:
        raise SourceDownloadError(f"{source.source_id}: received an empty HTML response.")

    downloaded_at = datetime.now(timezone.utc)
    directory: Path | None = None
    try:
        root = Path(output_dir)
        root.mkdir(parents=True, exist_ok=True)
        directory = Path(mkdtemp(
            prefix=f"{source.source_id}-{downloaded_at:%Y%m%dT%H%M%SZ}-", dir=root
        ))
        filename = f"{source.source_id}.html"
        with (directory / filename).open("xb") as stream:
            stream.write(content)
        snapshot = SourceSnapshot(
            snapshot_id=directory.name,
            source=source,
            downloaded_at=downloaded_at.isoformat().replace("+00:00", "Z"),
            resolved_url=resolved_url,
            http_status=status,
            content_type=content_type,
            charset=charset,
            size_bytes=len(content),
            sha256=sha256(content).hexdigest(),
            local_path=filename,
        )
        # The final manifest name only appears after its complete record is written.
        pending = directory / "manifest.json.partial"
        with pending.open("x", encoding="utf-8") as stream:
            json.dump({"schema_version": 1, "snapshot": asdict(snapshot)}, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
        pending.replace(directory / "manifest.json")
    except OSError as exc:
        if directory is not None:
            shutil.rmtree(directory, ignore_errors=True)
        raise SourceDownloadError(f"{source.source_id}: cannot save snapshot under '{output_dir}': {exc}") from exc
    return snapshot
