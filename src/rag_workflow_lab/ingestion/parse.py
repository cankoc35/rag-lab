"""Offline parser for the DocBook HTML structure in the PostgreSQL pilot.

Keep ordered content blocks, heading paths, SQL whitespace and table cells.
Only the saved source's configured scope is extracted. Markdown and arbitrary
web layouts are not supported by this parser version.
"""

from dataclasses import asdict, dataclass, field
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re

from rag_workflow_lab.contracts import (
    ParsedBlock, ParsedDocument, SourceSnapshot, SourceSpec, TableCell,
)


PARSER_VERSION = "postgresql-html-v1"
_VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
_SKIP_TAGS = {"script", "style", "nav", "header", "footer", "form", "noscript"}
_SKIP_CLASSES = {"navheader", "navfooter", "toc", "id_link", "indexterm"}
_INLINE_TAGS = {"a", "b", "br", "code", "em", "i", "img", "samp", "small", "span", "strong", "sub", "sup", "tt", "var", "wbr"}
_HEADINGS = {f"h{level}" for level in range(1, 7)}
_ADMONITIONS = {"note", "tip", "warning", "caution", "important"}


class SourceParseError(ValueError):
    """A saved snapshot is invalid or its selected HTML scope cannot be parsed."""


@dataclass
class _Node:
    tag: str
    attrs: dict[str, str | None] = field(default_factory=dict)
    children: list["_Node | str"] = field(default_factory=list)
    parent: "_Node | None" = field(default=None, repr=False)

    @property
    def classes(self) -> set[str]:
        return set((self.attrs.get("class") or "").split())

    def descendants(self):
        yield self
        for child in self.children:
            if isinstance(child, _Node):
                yield from child.descendants()


class _HTMLTree(HTMLParser):
    """Small tree builder for saved, explicitly closed PostgreSQL DocBook HTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _Node("document")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = _Node(tag, dict(attrs), parent=self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in _VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in _VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in _VOID_TAGS:
            return
        if len(self.stack) == 1 or self.stack[-1].tag != tag:
            raise SourceParseError(f"Unexpected closing HTML tag: </{tag}>.")
        self.stack.pop()

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def _skip(node: _Node) -> bool:
    return (
        node.tag in _SKIP_TAGS or bool(node.classes & _SKIP_CLASSES)
        or "hidden" in node.attrs or node.attrs.get("role") in {"navigation", "search"}
    )


def _raw_text(node: _Node, *, cell: bool = False) -> str:
    if _skip(node):
        return ""
    if node.tag == "br":
        return "\n"
    if node.tag == "img":
        return node.attrs.get("alt") or ""
    text = "".join(child if isinstance(child, str) else _raw_text(child, cell=cell)
                   for child in node.children)
    # Paragraph/list boundaries inside a cell carry meaning (name/type/description).
    if cell and node.tag in {"p", "li", "dt", "dd", "pre"}:
        return "\n" + text + "\n"
    return text


def _prose(text: str) -> str:
    return " ".join(text.split())


def _is_section(node: _Node) -> bool:
    return node.tag == "section" or any(re.fullmatch(r"sect[1-6]", c) for c in node.classes)


def _heading(node: _Node) -> tuple[int, str] | None:
    for item in node.descendants():
        if item.tag in _HEADINGS and not _skip(item):
            return int(item.tag[1]), _prose(_raw_text(item))
    return None


def _table_rows(table: _Node) -> tuple[tuple[TableCell, ...], ...]:
    rows = []
    for node in table.descendants():
        if node is not table and node.tag == "table":
            raise SourceParseError("Nested content tables are not supported.")
        if node.tag != "tr":
            continue
        cells = []
        for cell in node.children:
            if not isinstance(cell, _Node) or cell.tag not in {"td", "th"}:
                continue
            try:
                rowspan = int(cell.attrs.get("rowspan") or "1")
                colspan = int(cell.attrs.get("colspan") or "1")
            except ValueError as exc:
                raise SourceParseError("Invalid table cell span.") from exc
            if rowspan < 1 or colspan < 1:
                raise SourceParseError("Table cell spans must be positive.")
            text = "\n".join(filter(None, (_prose(line) for line in _raw_text(cell, cell=True).splitlines())))
            cells.append(TableCell(text, cell.tag == "th", rowspan, colspan))
        if cells:
            rows.append(tuple(cells))
    if not rows:
        raise SourceParseError("Selected content contains a table without cells.")
    return tuple(rows)


def parse_html(content: bytes, snapshot: SourceSnapshot) -> ParsedDocument:
    """Parse verified snapshot bytes without network access or writes.

    This version expects #docContent and explicitly closed DocBook tags. Fail
    on missing/ambiguous/overlapping selected sections instead of widening scope.
    """
    if snapshot.source.format != "html":
        raise SourceParseError("This parser supports HTML sources only.")
    if type(snapshot.size_bytes) is not int or len(content) != snapshot.size_bytes:
        raise SourceParseError("Snapshot byte size does not match its manifest.")
    if sha256(content).hexdigest() != snapshot.sha256:
        raise SourceParseError("Snapshot SHA-256 does not match its manifest.")
    if not isinstance(snapshot.snapshot_id, str) or not snapshot.snapshot_id.strip():
        raise SourceParseError("Snapshot ID must be a non-empty string.")
    try:
        html = content.decode(snapshot.charset or "utf-8")
    except (LookupError, UnicodeError, TypeError) as exc:
        raise SourceParseError(f"Cannot decode HTML with charset {snapshot.charset!r}.") from exc
    tree = _HTMLTree()
    try:
        tree.feed(html)
        tree.close()
    except (RecursionError, AssertionError) as exc:
        raise SourceParseError("Cannot parse the saved HTML structure.") from exc
    if len(tree.stack) != 1:
        raise SourceParseError("Saved HTML contains unclosed tags.")
    bodies = [n for n in tree.root.descendants() if n.attrs.get("id") == "docContent"]
    if len(bodies) != 1:
        raise SourceParseError("Expected exactly one PostgreSQL #docContent container.")
    body = bodies[0]
    selection = snapshot.source.selection
    if selection.mode == "page" and not selection.section_ids:
        roots = [body]
    elif selection.mode == "sections" and selection.section_ids:
        if len(set(selection.section_ids)) != len(selection.section_ids):
            raise SourceParseError("Selected section IDs must be unique.")
        roots = []
        for section_id in selection.section_ids:
            matches = [n for n in body.descendants() if n.attrs.get("id") == section_id]
            if len(matches) != 1 or not _is_section(matches[0]):
                raise SourceParseError(f"Expected exactly one content section with ID {section_id!r}.")
            roots.append(matches[0])
        selected = {id(node) for node in roots}
        for root in roots:
            parent = root.parent
            while parent is not None:
                if _skip(parent):
                    raise SourceParseError("Selected section is inside excluded navigation/hidden content.")
                if id(parent) in selected:
                    raise SourceParseError("Selected sections overlap.")
                parent = parent.parent
        # Preserve document order regardless of the order in the allowlist.
        roots = [n for n in body.descendants() if id(n) in selected]
    else:
        raise SourceParseError("Invalid page/sections selection.")

    blocks: list[ParsedBlock] = []
    headings: list[tuple[int, str]] = []

    def emit(kind, text, anchor, rows=()):
        if text:
            blocks.append(ParsedBlock(kind, text, tuple(title for _, title in headings), anchor, rows))

    def walk(node: _Node, anchor: str | None):
        if _skip(node):
            return
        anchor = node.attrs.get("id") or anchor
        if node.tag in _HEADINGS:
            title = _prose(_raw_text(node))
            level = int(node.tag[1])
            if node.parent and node.parent.classes & _ADMONITIONS and headings:
                # DocBook uses h3 for a Note even inside an h3 section.
                level = max(level, headings[-1][0] + 1)
            while headings and headings[-1][0] >= level:
                headings.pop()
            headings.append((level, title))
            for link in node.descendants():
                href = link.attrs.get("href") or ""
                if "id_link" in link.classes and href.startswith("#"):
                    anchor = href[1:] or anchor
            emit("heading", title, anchor)
        elif node.tag == "pre":
            emit("code", _raw_text(node).strip("\r\n"), anchor)
        elif node.tag == "table":
            rows = _table_rows(node)
            emit("table", "\n".join("\t".join(c.text for c in row) for row in rows), anchor, rows)
        elif node.tag == "p":
            emit("paragraph", _prose(_raw_text(node)), anchor)
        else:
            saved_headings = headings.copy()
            pending: list[str] = []

            def flush():
                emit("paragraph", _prose("".join(pending)), anchor)
                pending.clear()

            for child in node.children:
                if isinstance(child, str):
                    pending.append(child)
                elif child.tag in _INLINE_TAGS:
                    pending.append(_raw_text(child))
                else:
                    flush()
                    walk(child, anchor)
            flush()
            if _is_section(node) or node.classes & _ADMONITIONS:
                headings[:] = saved_headings

    for root in roots:
        ancestors = []
        parent = root.parent
        while parent is not None and parent is not body:
            ancestors.append(parent)
            parent = parent.parent
        headings.clear()
        for ancestor in reversed(ancestors):
            if _is_section(ancestor) and (heading := _heading(ancestor)):
                headings.append(heading)
        walk(root, None)
    if not blocks or not any(block.kind == "heading" for block in blocks):
        raise SourceParseError("Selected scope contains no headed document content.")
    return ParsedDocument(
        source_id=snapshot.source.source_id,
        snapshot_id=snapshot.snapshot_id,
        source_url=snapshot.source.url,
        title=snapshot.source.title,
        source_sha256=snapshot.sha256,
        parser_version=PARSER_VERSION,
        blocks=tuple(blocks),
    )


def parse_snapshot(manifest_path: str | Path, source: SourceSpec) -> ParsedDocument:
    """Read a saved manifest/HTML pair and match it to an allowlisted source.

    Only a local file beside the manifest is read; input files are never changed.
    """
    path = Path(manifest_path)
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(record, dict) or type(record.get("schema_version")) is not int or record["schema_version"] != 1:
            raise SourceParseError("Snapshot manifest schema_version must be the integer 1.")
        metadata = record.get("snapshot")
        if not isinstance(metadata, dict) or metadata.get("source") != json.loads(json.dumps(asdict(source))):
            raise SourceParseError("Snapshot source differs from the selected source definition.")
        fields = {key: value for key, value in metadata.items() if key != "source"}
        snapshot = SourceSnapshot(source=source, **fields)
        if snapshot.http_status != 200 or snapshot.content_type not in {"text/html", "application/xhtml+xml"} or snapshot.resolved_url != source.url:
            raise SourceParseError("Snapshot must record a successful HTML response from the selected URL.")
        local = snapshot.local_path
        if not isinstance(local, str) or not local or Path(local).name != local or local in {".", ".."}:
            raise SourceParseError("Snapshot local_path must be a filename beside its manifest.")
        html_path = path.parent / local
        if html_path.resolve().parent != path.parent.resolve():
            raise SourceParseError("Snapshot HTML must remain beside its manifest.")
        content = html_path.read_bytes()
    except SourceParseError:
        raise
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        raise SourceParseError(f"Cannot read snapshot '{path}': {exc}") from exc
    return parse_html(content, snapshot)
