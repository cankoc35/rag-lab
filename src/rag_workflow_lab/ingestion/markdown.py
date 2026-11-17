"""Offline ingestion for Atlas Markdown: headings, prose, pipe tables and fences.

This is a scoped reader, not a general Markdown implementation. Inline markup
is retained. Lists remain paragraph text; tables require outer pipes and do
not support escaped pipes. Code fences use three backticks on their own lines.
"""

from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
from tempfile import mkdtemp

from rag_workflow_lab.contracts import ParsedBlock, ParsedDocument, TableCell
from rag_workflow_lab.ingestion.parse import SourceParseError


PARSER_VERSION = "atlas-markdown-v1"


def parse_markdown(content: bytes, *, source_id: str, snapshot_id: str,
                   source_url: str, title: str) -> ParsedDocument:
    """Preserve block order and heading context; anchors identify source lines."""
    lines = content.decode("utf-8").splitlines()
    blocks = []
    headings = []
    index = 0

    def emit(kind, text, start, rows=()):
        blocks.append(ParsedBlock(kind, text, tuple(name for _, name in headings), f"L{start + 1}", rows))

    def cells(line):
        line = line.strip()
        if not line.startswith("|") or not line.endswith("|") or "\\|" in line:
            raise SourceParseError("Markdown tables require outer pipes and no escaped pipes.")
        return [cell.strip() for cell in line[1:-1].split("|")]

    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        start = index
        if heading := re.fullmatch(r"(#{1,6}) +(.+)", line):
            level, name = len(heading[1]), heading[2].strip()
            while headings and headings[-1][0] >= level:
                headings.pop()
            headings.append((level, name))
            emit("heading", name, start)
            index += 1
        elif line.startswith("```"):
            if not re.fullmatch(r"```[A-Za-z0-9_-]*\s*", line):
                raise SourceParseError("Unsupported Markdown code fence.")
            index += 1
            while index < len(lines) and lines[index] != "```":
                index += 1
            if index == len(lines):
                raise SourceParseError("Unclosed Markdown code fence.")
            emit("code", "\n".join(lines[start + 1:index]), start)
            index += 1
        elif line.startswith("|"):
            header = cells(line)
            if index + 1 == len(lines):
                raise SourceParseError("Markdown table has no separator row.")
            separator = cells(lines[index + 1])
            if len(separator) != len(header) or not all(re.fullmatch(r":?-{3,}:?", cell) for cell in separator):
                raise SourceParseError("Invalid Markdown table separator.")
            rows = [tuple(TableCell(text, is_header=True) for text in header)]
            index += 2
            while index < len(lines) and lines[index].startswith("|"):
                values = cells(lines[index])
                if len(values) != len(header):
                    raise SourceParseError("Markdown table rows have inconsistent column counts.")
                rows.append(tuple(TableCell(text) for text in values))
                index += 1
            rows = tuple(rows)
            emit("table", "\n".join("\t".join(cell.text for cell in row) for row in rows), start, rows)
        else:
            index += 1
            while index < len(lines) and lines[index].strip() and not re.match(r"#{1,6} |```|\|", lines[index]):
                index += 1
            emit("paragraph", "\n".join(lines[start:index]), start)

    if not any(block.kind == "heading" for block in blocks):
        raise SourceParseError("Markdown source must contain a heading.")
    return ParsedDocument(source_id, snapshot_id, source_url, title,
                          sha256(content).hexdigest(), PARSER_VERSION, tuple(blocks))


def ingest_markdown(manifest_path: str | Path, output_dir: str | Path) -> dict:
    """Validate the complete local allowlist, then save new snapshots and blocks.

    Paths are filenames beside the manifest. Earlier runs are never overwritten;
    no source discovery, network, tokenizer, model or database access is used.
    """
    manifest_path = Path(manifest_path).resolve()
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    if not isinstance(manifest, dict) or type(manifest.get("schema_version")) is not int or manifest["schema_version"] != 1:
        raise ValueError("Markdown manifest schema_version must be the integer 1.")
    state = manifest.get("document_state")
    sources = manifest.get("sources")
    if not isinstance(state, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", state):
        raise ValueError("Markdown document_state must use letters, digits, underscores or hyphens.")
    if not isinstance(sources, list) or not sources:
        raise ValueError("Markdown manifest sources must be a non-empty list.")

    prepared = []
    seen_ids, seen_paths = set(), set()
    for source in sources:
        if not isinstance(source, dict) or any(not isinstance(source.get(key), str) or not source[key].strip()
                for key in ("source_id", "title", "format", "path", "document_version", "sha256")):
            raise ValueError("Each Markdown source requires source_id, title, format, path, document_version and sha256.")
        source_id, filename = source["source_id"], source["path"]
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", source_id) or source_id in seen_ids:
            raise ValueError("Markdown source IDs must be valid and unique.")
        if source["format"] != "markdown" or Path(filename).name != filename or not filename.endswith(".md") or filename in seen_paths:
            raise ValueError("Markdown paths must be unique .md filenames beside the manifest.")
        path = (manifest_path.parent / filename).resolve()
        if path.parent != manifest_path.parent:
            raise ValueError("Markdown source must remain beside its manifest.")
        content = path.read_bytes()
        if sha256(content).hexdigest() != source["sha256"]:
            raise ValueError(f"Markdown source SHA-256 mismatch: {source_id}")
        seen_ids.add(source_id)
        seen_paths.add(filename)
        source = {**source, "url": path.as_uri()}
        identity = json.dumps({"source": source, "document_state": state}, sort_keys=True).encode()
        snapshot_id = f"{source_id}-{sha256(identity).hexdigest()[:16]}"
        document = parse_markdown(content, source_id=source_id, snapshot_id=snapshot_id,
                                  source_url=source["url"], title=source["title"])
        snapshot = {
            "snapshot_id": snapshot_id, "source": source, "document_state": state,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "size_bytes": len(content), "sha256": document.source_sha256,
            "local_path": filename, "source_manifest_sha256": sha256(manifest_bytes).hexdigest(),
        }
        prepared.append((content, snapshot, document))

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    run_dir = Path(mkdtemp(prefix=f"{state}-", dir=root))
    results = []
    try:
        for content, snapshot, document in prepared:
            folder = run_dir / snapshot["snapshot_id"]
            folder.mkdir()
            (folder / snapshot["local_path"]).write_bytes(content)
            for name, payload in (("manifest.json", {"schema_version": 1, "snapshot": snapshot}),
                                  ("parsed.json", {"schema_version": 1, "document": asdict(document)})):
                (folder / name).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            results.append({"source_id": document.source_id, "snapshot_id": document.snapshot_id,
                            "blocks": len(document.blocks), "manifest_path": str(folder / "manifest.json"),
                            "parsed_path": str(folder / "parsed.json")})
    except OSError:
        shutil.rmtree(run_dir)
        raise
    return {"output_dir": str(run_dir), "document_state": state, "sources": results}


def load_markdown_snapshots(sources_manifest: Path, run_dir: Path) -> list[tuple[Path, ParsedDocument]]:
    """Reparse pinned snapshot copies and verify their saved block records."""
    sources_manifest = sources_manifest.resolve()
    allowlist_bytes = sources_manifest.read_bytes()
    allowlist = json.loads(allowlist_bytes)
    if type(allowlist.get("schema_version")) is not int or allowlist["schema_version"] != 1:
        raise ValueError("Markdown manifest schema_version must be the integer 1.")
    documents, seen = [], set()
    for source in allowlist["sources"]:
        source_id, filename = source["source_id"], source["path"]
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", source_id) or source_id in seen:
            raise ValueError("Markdown source IDs must be valid and unique.")
        if Path(filename).name != filename or not filename.endswith(".md"):
            raise ValueError("Markdown snapshot paths must be .md filenames.")
        seen.add(source_id)
        candidates = sorted(run_dir.glob(f"{source_id}-*/manifest.json"))
        if len(candidates) != 1:
            raise ValueError(f"Expected one Markdown snapshot for {source_id}, found {len(candidates)}.")
        path = candidates[0]
        if path.resolve().parent.parent != run_dir.resolve():
            raise ValueError("Markdown snapshot must remain inside the selected run.")
        expected_source = {**source, "url": (sources_manifest.parent / filename).as_uri()}
        identity = json.dumps({"source": expected_source, "document_state": allowlist["document_state"]}, sort_keys=True).encode()
        expected = {
            "snapshot_id": f"{source_id}-{sha256(identity).hexdigest()[:16]}",
            "source": expected_source, "document_state": allowlist["document_state"],
            "source_manifest_sha256": sha256(allowlist_bytes).hexdigest(),
            "local_path": filename, "sha256": source["sha256"],
        }
        record = json.loads(path.read_bytes())
        snapshot = record["snapshot"]
        if type(record.get("schema_version")) is not int or record["schema_version"] != 1 or any(snapshot.get(key) != value for key, value in expected.items()):
            raise ValueError(f"Markdown snapshot metadata differs from the allowlist: {source_id}")
        raw_path = path.parent / filename
        if raw_path.resolve().parent != path.parent.resolve():
            raise ValueError("Markdown snapshot copy must remain beside its manifest.")
        content = raw_path.read_bytes()
        if sha256(content).hexdigest() != source["sha256"] or len(content) != snapshot["size_bytes"] or snapshot["snapshot_id"] != path.parent.name:
            raise ValueError(f"Markdown snapshot identity, size or SHA-256 mismatch: {source_id}")
        document = parse_markdown(content, source_id=source_id, snapshot_id=snapshot["snapshot_id"],
                                  source_url=expected_source["url"], title=source["title"])
        saved = json.loads(path.with_name("parsed.json").read_bytes())
        if saved.get("schema_version") != 1 or saved.get("document") != json.loads(json.dumps(asdict(document))):
            raise ValueError(f"Saved Markdown blocks differ from reparsed source: {source_id}")
        documents.append((path, document))
    if not documents:
        raise ValueError("Markdown allowlist contains no sources.")
    return documents
