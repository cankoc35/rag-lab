"""Group whole parser blocks within section and token boundaries.

Pilot defaults: a 512-token soft target, a 1024-token application ceiling,
and no overlap. Every count includes the prefix, heading context and special
tokens. The caller supplies an untruncated, unpadded token counter; this
module never loads a model, downloads files or changes the input document.
"""

from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
from hashlib import sha256
import json

from rag_workflow_lab.contracts import Chunk, ParsedBlock, ParsedDocument, TokenizerSpec


CHUNKER_VERSION = "section-blocks-v1"
SERIALIZATION_VERSION = "chunk-context-v1"


class ChunkingError(ValueError):
    """Chunking cannot safely proceed with the supplied input or configuration."""


class ChunkOverflowError(ChunkingError):
    """One intact block exceeds the ceiling; no truncated output is returned."""

    def __init__(self, document: ParsedDocument, index: int, block: ParsedBlock,
                 token_count: int, max_tokens: int) -> None:
        self.source_id = document.source_id
        self.snapshot_id = document.snapshot_id
        self.block_index = index
        self.kind = block.kind
        self.token_count = token_count
        self.max_tokens = max_tokens
        super().__init__(
            f"{self.source_id}/{self.snapshot_id}: block {index} ({block.kind}) "
            f"requires {token_count} tokens including context; limit is {max_tokens}. "
            "The block was not split or truncated."
        )


@dataclass(frozen=True)
class ChunkSettings:
    """Limits apply to complete serialized inputs, not body text alone."""

    target_tokens: int = 512
    max_tokens: int = 1024
    document_prefix: str = "search_document: "


def serialize_chunk(text: str, heading_path: tuple[str, ...], *,
                    document_prefix: str = "search_document: ") -> str:
    """Return the exact text to count and later embed; preserve body whitespace."""
    context = " > ".join(heading_path)
    return document_prefix + (context + "\n\n" if context else "") + text


def _digest(value: dict) -> str:
    data = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return sha256(data.encode("utf-8")).hexdigest()


def chunk_document(
    document: ParsedDocument, *, count_tokens: Callable[[str], int],
    tokenizer: TokenizerSpec, settings: ChunkSettings = ChunkSettings(),
) -> tuple[Chunk, ...]:
    """Return deterministic chunks from one source snapshot, with no overlap.

    Headings are context, not standalone chunks. Within each contiguous
    heading section, pair an immediately preceding paragraph with code/table
    when their complete input fits max_tokens. This is an adjacency heuristic,
    not semantic classification. Greedily pack these units up to target_tokens;
    a larger intact unit may stand alone up to max_tokens. Never split a block.
    An oversized paragraph also raises rather than silently losing text.

    count_tokens must count the entire string with special tokens enabled,
    padding/truncation disabled. TokenizerSpec must identify that exact setup.
    Empty or heading-only documents return an empty tuple. The function
    returns no partial result if any content block exceeds the ceiling.
    """
    for name, value in (("target_tokens", settings.target_tokens),
                        ("max_tokens", settings.max_tokens),
                        ("max_input_tokens", tokenizer.max_input_tokens)):
        if type(value) is not int or value <= 0:
            raise ChunkingError(f"{name} must be a positive integer.")
    if settings.target_tokens > settings.max_tokens:
        raise ChunkingError("target_tokens must not exceed max_tokens.")
    if settings.max_tokens > tokenizer.max_input_tokens:
        raise ChunkingError("max_tokens exceeds the tokenizer/model input budget.")
    if not isinstance(settings.document_prefix, str):
        raise ChunkingError("document_prefix must be a string.")
    for name in ("identifier", "revision", "fingerprint"):
        value = getattr(tokenizer, name)
        if not isinstance(value, str) or not value.strip():
            raise ChunkingError(f"Tokenizer {name} must be a nonempty string.")

    # A heading boundary always ends a run, even when two titles are identical.
    # Preserve original block positions so evidence can be mapped back exactly.
    sections: list[list[tuple[int, ParsedBlock]]] = []
    section: list[tuple[int, ParsedBlock]] = []
    for index, block in enumerate(document.blocks, start=1):
        if block.kind not in {"heading", "paragraph", "code", "table"}:
            raise ChunkingError(f"Unsupported block kind at position {index}: {block.kind}")
        if not isinstance(block.text, str) or not block.text.strip():
            raise ChunkingError(f"Empty block text at position {index}.")
        if (not isinstance(block.heading_path, tuple)
                or any(not isinstance(h, str) or not h.strip() for h in block.heading_path)):
            raise ChunkingError(f"Invalid heading path at position {index}.")
        if block.kind == "heading":
            if section:
                sections.append(section)
                section = []
            continue
        if section and block.heading_path != section[-1][1].heading_path:
            sections.append(section)
            section = []
        section.append((index, block))
    if section:
        sections.append(section)

    def render(items: list[tuple[int, ParsedBlock]]) -> tuple[str, str, int]:
        body = "\n\n".join(block.text for _, block in items)
        embedding_text = serialize_chunk(
            body, items[0][1].heading_path, document_prefix=settings.document_prefix,
        )
        size = count_tokens(embedding_text)
        if type(size) is not int or size <= 0:
            raise ChunkingError("count_tokens must return a positive integer.")
        return body, embedding_text, size

    # Validate every atomic input before building any output.
    for section in sections:
        for index, block in section:
            size = render([(index, block)])[2]
            if size > settings.max_tokens:
                raise ChunkOverflowError(document, index, block, size, settings.max_tokens)

    groups: list[list[tuple[int, ParsedBlock]]] = []
    for section in sections:
        units: list[list[tuple[int, ParsedBlock]]] = []
        position = 0
        while position < len(section):
            unit = section[position:position + 1]
            if (position + 1 < len(section) and unit[0][1].kind == "paragraph"
                    and section[position + 1][1].kind in {"code", "table"}):
                pair = section[position:position + 2]
                if render(pair)[2] <= settings.max_tokens:
                    unit = pair
            units.append(unit)
            position += len(unit)

        pending: list[tuple[int, ParsedBlock]] = []
        for unit in units:
            if pending and render(pending + unit)[2] > settings.target_tokens:
                groups.append(pending)
                pending = []
            pending.extend(unit)
            if render(pending)[2] >= settings.target_tokens:
                groups.append(pending)
                pending = []
        if pending:
            groups.append(pending)

    identity = {
        "document_sha256": _digest(asdict(document)),
        "chunker_version": CHUNKER_VERSION,
        "serialization_version": SERIALIZATION_VERSION,
        "settings": asdict(settings),
        "tokenizer": asdict(tokenizer),
        "overlap_tokens": 0,
    }
    chunks = []
    for group in groups:
        text, embedding_text, size = render(group)
        # Count complete groups again: counts of separately encoded pieces are
        # not additive, so individual block sizes cannot enforce this invariant.
        if size > settings.max_tokens:
            raise ChunkingError("Combined chunk exceeds max_tokens; no chunks returned.")
        indices = tuple(index for index, _ in group)
        chunk_id = document.source_id + "-" + _digest({
            **identity, "block_indices": indices, "embedding_text": embedding_text,
            "token_count": size,
        })
        chunks.append(Chunk(
            chunk_id=chunk_id, source_id=document.source_id,
            snapshot_id=document.snapshot_id, source_url=document.source_url,
            source_sha256=document.source_sha256, parser_version=document.parser_version,
            chunker_version=CHUNKER_VERSION, serialization_version=SERIALIZATION_VERSION,
            tokenizer=tokenizer, target_tokens=settings.target_tokens,
            max_tokens=settings.max_tokens, document_prefix=settings.document_prefix,
            heading_path=group[0][1].heading_path,
            anchors=tuple(dict.fromkeys(block.anchor for _, block in group if block.anchor)),
            block_indices=indices, blocks=tuple(block for _, block in group),
            text=text, embedding_text=embedding_text, token_count=size,
        ))
    return tuple(replace(
        chunk,
        previous_chunk_id=chunks[index - 1].chunk_id if index else None,
        next_chunk_id=chunks[index + 1].chunk_id if index + 1 < len(chunks) else None,
    ) for index, chunk in enumerate(chunks))
