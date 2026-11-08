"""Local Nomic document/query embeddings, with explicit loading and no downloads.

The standard-library API remains importable without ML dependencies. Loading
requires an already downloaded, checksummed model snapshot. Document inputs
are the chunker's existing embedding_text; query inputs are raw question text.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Literal, Protocol

from rag_workflow_lab.config import EmbeddingSettings


MODEL_ID = "nomic-ai/nomic-embed-text-v1.5"
MODEL_REVISION = "e9b6763023c676ca8431644204f50c2b100d9aab"
DIMENSIONS = 768
ADAPTER_VERSION = "nomic-local-v1"
DOCUMENT_PREFIX = "search_document: "
QUERY_PREFIX = "search_query: "
NORMALIZATION = "mean-pooling -> layer-norm-768 (eps=1e-5) -> L2"
MODEL_FILES = (
    "model.safetensors", "config.json", "modules.json", "sentence_bert_config.json",
    "config_sentence_transformers.json", "tokenizer.json", "tokenizer_config.json",
    "special_tokens_map.json", "vocab.txt", "1_Pooling/config.json",
)


class EmbeddingError(ValueError):
    """The input or local model cannot safely produce a compatible embedding."""


@dataclass(frozen=True)
class EmbeddingResult:
    task: Literal["document", "query"]
    model_id: str
    model_revision: str
    adapter_version: str
    input_sha256: str
    token_count: int
    vector: tuple[float, ...]


class EmbeddingBackend(Protocol):
    """Small inference seam; tests supply a fake without ML packages."""

    max_tokens: int

    def complete_token_ids(self, text: str) -> tuple[int, ...]: ...
    def forward_token_ids(self, text: str) -> tuple[int, ...]: ...
    def encode_normalized(self, text: str) -> tuple[float, ...]: ...


def file_sha256(path: Path) -> str:
    """Hash large weight files without holding a second copy in memory."""
    checksum = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def verify_model_files(settings: EmbeddingSettings) -> dict:
    """Read-only integrity check. Only the opt-in download script writes a manifest."""
    path = settings.model_dir / "model_manifest.json"
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if (manifest["schema_version"] != 1 or manifest["model_id"] != settings.model_id
                or manifest["revision"] != settings.revision or set(manifest["files"]) != set(MODEL_FILES)):
            raise EmbeddingError("Model manifest does not match the configured snapshot.")
        for name in MODEL_FILES:
            record = manifest["files"][name]
            file_path = settings.model_dir / name
            if file_path.stat().st_size != record["size_bytes"] or file_sha256(file_path) != record["sha256"]:
                raise EmbeddingError(f"Model file checksum mismatch: {name}")
        return manifest
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise EmbeddingError(
            f"Missing/invalid local model at {settings.model_dir}. "
            "Run scripts/embedding_smoke.py --download-model explicitly first."
        ) from exc


class _SentenceTransformerBackend:
    def __init__(self, model, max_tokens: int) -> None:
        self.model = model
        self.max_tokens = max_tokens

    def complete_token_ids(self, text: str) -> tuple[int, ...]:
        return tuple(self.model.tokenizer.encode(
            text, add_special_tokens=True, truncation=False, padding=False,
        ))

    def forward_token_ids(self, text: str) -> tuple[int, ...]:
        return tuple(self.model.tokenize([text])["input_ids"][0].tolist())

    def encode_normalized(self, text: str) -> tuple[float, ...]:
        import torch.nn.functional as functional

        # Prefixes are already part of text. Empty prompt disables implicit
        # prompt insertion, preventing duplicate task prefixes.
        vectors = self.model.encode(
            [text], prompt="", batch_size=1, show_progress_bar=False,
            convert_to_tensor=True, normalize_embeddings=False,
        )
        vectors = functional.layer_norm(vectors.float(), (DIMENSIONS,), eps=1e-5)
        vectors = functional.normalize(vectors, p=2, dim=-1)
        return tuple(vectors[0].cpu().tolist())


class NomicEmbedder:
    """One pinned model/revision for documents and queries, CPU float32 initially."""

    def __init__(self, settings: EmbeddingSettings, backend: EmbeddingBackend) -> None:
        if settings.model_id != MODEL_ID or settings.revision != MODEL_REVISION:
            raise EmbeddingError("This adapter requires the pinned Nomic Embed Text v1.5 snapshot.")
        if settings.dimensions != DIMENSIONS or settings.device != "cpu":
            raise EmbeddingError("The initial adapter requires 768 dimensions on CPU.")
        if (type(settings.max_tokens) is not int or settings.max_tokens <= 0
                or settings.max_tokens > backend.max_tokens):
            raise EmbeddingError("Invalid application token budget for this backend.")
        self.settings = settings
        self.backend = backend

    @classmethod
    def from_local(cls, settings: EmbeddingSettings) -> "NomicEmbedder":
        """Load only cached safetensors and native installed code, never from the network."""
        verify_model_files(settings)
        try:
            import torch
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise EmbeddingError("Install the optional embeddings dependencies or use the smoke script.") from exc
        torch.set_num_threads(2)
        model = SentenceTransformer(
            str(settings.model_dir), device="cpu", local_files_only=True,
            trust_remote_code=False,
            model_kwargs={"torch_dtype": torch.float32, "attn_implementation": "eager"},
        )
        if model.get_sentence_embedding_dimension() != DIMENSIONS:
            raise EmbeddingError("Loaded model has an unexpected embedding dimension.")
        # This first adapter stays inside the native base context; extending
        # RoPE beyond it is a separate, unverified configuration.
        supported = min(model.max_seq_length, model[0].auto_model.config.max_position_embeddings)
        if supported < settings.max_tokens:
            raise EmbeddingError("Configured token budget exceeds the loaded model's sequence limit.")
        if not type(model[0].auto_model).__module__.startswith("transformers.models.nomic_bert."):
            raise EmbeddingError("Expected the installed Transformers native NomicBERT implementation.")
        model.max_seq_length = settings.max_tokens
        model.eval()
        return cls(settings, _SentenceTransformerBackend(model, settings.max_tokens))

    def count_tokens(self, text: str) -> int:
        """Count complete inputs, including special tokens, without truncation/padding."""
        return len(self.backend.complete_token_ids(text))

    def _embed(self, text: str, task: Literal["document", "query"]) -> EmbeddingResult:
        complete = self.backend.complete_token_ids(text)
        if not complete or len(complete) > self.settings.max_tokens:
            raise EmbeddingError(
                f"{task} input has {len(complete)} tokens; limit is {self.settings.max_tokens}. "
                "No embedding was produced; input was not truncated."
            )
        if self.backend.forward_token_ids(text) != complete:
            raise EmbeddingError("Model tokenization changes or truncates the complete input.")
        vector = self.backend.encode_normalized(text)
        if len(vector) != DIMENSIONS or not all(math.isfinite(v) for v in vector):
            raise EmbeddingError("Embedding must contain 768 finite values.")
        if not math.isclose(math.sqrt(sum(v * v for v in vector)), 1.0, abs_tol=1e-5):
            raise EmbeddingError("Embedding is not L2-normalized.")
        return EmbeddingResult(
            task=task, model_id=self.settings.model_id, model_revision=self.settings.revision,
            adapter_version=ADAPTER_VERSION, input_sha256=sha256(text.encode("utf-8")).hexdigest(),
            token_count=len(complete), vector=tuple(vector),
        )

    def embed_document(self, embedding_text: str) -> EmbeddingResult:
        """Embed existing chunk.embedding_text without adding its document prefix again."""
        if (not isinstance(embedding_text, str) or not embedding_text.startswith(DOCUMENT_PREFIX)
                or not embedding_text[len(DOCUMENT_PREFIX):].strip()
                or embedding_text.startswith(DOCUMENT_PREFIX + DOCUMENT_PREFIX)
                or embedding_text.startswith(DOCUMENT_PREFIX + QUERY_PREFIX)):
            raise EmbeddingError("Document input must have exactly one leading search_document prefix.")
        return self._embed(embedding_text, "document")

    def embed_query(self, question: str) -> EmbeddingResult:
        """Accept only a raw nonempty question, then add the query prefix once."""
        if (not isinstance(question, str) or not question.strip()
                or question.lstrip().startswith((QUERY_PREFIX.strip(), DOCUMENT_PREFIX.strip()))):
            raise EmbeddingError("Query input must be raw question text without a task prefix.")
        return self._embed(QUERY_PREFIX + question, "query")
