"""Shared data contracts without framework, database or I/O dependencies."""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class SourceSelection:
    """Select the document body or complete subtrees of named HTML sections."""

    mode: Literal["page", "sections"]
    section_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class SourceSpec:
    """A source definition; downloaded snapshot metadata is recorded separately."""

    source_id: str
    title: str
    url: str
    format: Literal["html"]
    postgresql_version: str
    selection: SourceSelection


@dataclass(frozen=True)
class SourceSnapshot:
    """One downloaded source; local_path is relative to its manifest directory."""

    snapshot_id: str
    source: SourceSpec
    downloaded_at: str
    resolved_url: str
    http_status: int
    content_type: str
    charset: str | None
    size_bytes: int
    sha256: str
    local_path: str


@dataclass(frozen=True)
class TableCell:
    """A table cell; retain header and span information rather than flattening it."""

    text: str
    is_header: bool = False
    rowspan: int = 1
    colspan: int = 1


@dataclass(frozen=True)
class ParsedBlock:
    """An ordered content block with its heading context and citation anchor."""

    kind: Literal["heading", "paragraph", "code", "table"]
    text: str
    heading_path: tuple[str, ...]
    anchor: str | None
    table_rows: tuple[tuple[TableCell, ...], ...] = ()


@dataclass(frozen=True)
class ParsedDocument:
    """Parsed evidence from one snapshot; blocks are not embedding chunks yet."""

    source_id: str
    snapshot_id: str
    source_url: str
    title: str
    source_sha256: str
    parser_version: str
    blocks: tuple[ParsedBlock, ...]


@dataclass(frozen=True)
class TokenizerSpec:
    """Identity of the counting setup, including files, backend and settings.

    fingerprint identifies that complete setup, not just the model name.
    max_input_tokens includes model special tokens.
    """

    identifier: str
    revision: str
    fingerprint: str
    max_input_tokens: int


@dataclass(frozen=True)
class Chunk:
    """One embedding input with intact source blocks and reproducible provenance.

    block_indices are one-based positions in ParsedDocument.blocks. Headings
    become heading_path context, rather than standalone embedding chunks.
    Neighbor links follow source order, including across section boundaries.
    """

    chunk_id: str
    source_id: str
    snapshot_id: str
    source_url: str
    source_sha256: str
    parser_version: str
    chunker_version: str
    serialization_version: str
    tokenizer: TokenizerSpec
    target_tokens: int
    max_tokens: int
    document_prefix: str
    heading_path: tuple[str, ...]
    anchors: tuple[str, ...]
    block_indices: tuple[int, ...]
    blocks: tuple[ParsedBlock, ...]
    text: str
    embedding_text: str
    token_count: int
    overlap_tokens: int = 0
    previous_chunk_id: str | None = None
    next_chunk_id: str | None = None
