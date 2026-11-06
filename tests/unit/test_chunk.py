"""Chunking invariants with synthetic blocks and a deterministic token counter.

No model files, third-party packages or network access are required. Counts
below exercise grouping logic; they are not estimates of a real tokenizer.
"""

from dataclasses import replace
from hashlib import sha256
import unittest
from unittest.mock import patch

from rag_workflow_lab.contracts import ParsedBlock, ParsedDocument, TableCell, TokenizerSpec
from rag_workflow_lab.ingestion.chunk import (
    ChunkingError, ChunkOverflowError, ChunkSettings, chunk_document, serialize_chunk,
)


def word_count(text):
    """Include two synthetic special tokens in every complete input."""
    return len(text.split()) + 2


def block(text, kind="paragraph", path=("Indexes",), anchor="INDEXES", rows=()):
    return ParsedBlock(kind, text, path, anchor, rows)


class ChunkDocumentTests(unittest.TestCase):
    def setUp(self):
        self.tokenizer = TokenizerSpec("synthetic-word-counter", "v1", "fixture-v1", 8192)
        self.settings = ChunkSettings(target_tokens=12, max_tokens=22)
        self.document = ParsedDocument(
            "PG-FIXTURE", "PG-FIXTURE-snapshot-1", "https://example.invalid/fixture",
            "Fixture", sha256(b"fixture").hexdigest(), "fixture-parser-v1", (),
        )
        network = patch("socket.create_connection", side_effect=AssertionError("Unexpected network access"))
        network.start()
        self.addCleanup(network.stop)

    def chunk(self, *blocks, **kwargs):
        return chunk_document(
            replace(self.document, blocks=blocks), count_tokens=kwargs.pop("count_tokens", word_count),
            tokenizer=kwargs.pop("tokenizer", self.tokenizer),
            settings=kwargs.pop("settings", self.settings), **kwargs,
        )

    def test_default_budgets_and_complete_input_serialization(self):
        chunks = self.chunk(block("SELECT *\n    FROM items;", "code"), settings=ChunkSettings())
        self.assertEqual(chunks[0].target_tokens, 512)
        self.assertEqual(chunks[0].max_tokens, 1024)
        self.assertEqual(chunks[0].embedding_text, "search_document: Indexes\n\nSELECT *\n    FROM items;")
        self.assertEqual(chunks[0].token_count, word_count(chunks[0].embedding_text))
        self.assertEqual(serialize_chunk("body\n", ()), "search_document: body\n")

    def test_paragraphs_group_at_whole_block_boundaries_without_overlap(self):
        blocks = tuple(block(" ".join([f"p{i}"] * 5)) for i in range(3))
        chunks = self.chunk(*blocks)
        self.assertEqual([c.block_indices for c in chunks], [(1,), (2,), (3,)])
        self.assertEqual([b for c in chunks for b in c.blocks], list(blocks))
        self.assertTrue(all(c.overlap_tokens == 0 for c in chunks))
        short = self.chunk(block("one two"), block("three four"))
        self.assertEqual(len(short), 1)
        self.assertEqual(short[0].text, "one two\n\nthree four")

    def test_intro_stays_with_long_code_up_to_hard_ceiling(self):
        sql = "SELECT 'semi;colon', $$dollar;quoted$$\n    FROM items\n    WHERE active = true;"
        intro, code = block("Consider this example:"), block(sql, "code", anchor="EXAMPLE")
        chunks = self.chunk(block("Earlier independent explanation."), intro, code)
        self.assertEqual([c.block_indices for c in chunks], [(1,), (2, 3)])
        self.assertGreater(chunks[1].token_count, self.settings.target_tokens)
        self.assertLessEqual(chunks[1].token_count, self.settings.max_tokens)
        self.assertEqual(chunks[1].blocks[1].text, sql)
        self.assertEqual(chunks[1].anchors, ("INDEXES", "EXAMPLE"))

    def test_pair_that_exceeds_ceiling_is_kept_as_separate_intact_blocks(self):
        paragraph = block(" ".join(["explanation"] * 12))
        code = block(" ".join(["sql"] * 12), "code")
        chunks = self.chunk(paragraph, code)
        self.assertEqual([c.block_indices for c in chunks], [(1,), (2,)])
        self.assertEqual([c.blocks[0] for c in chunks], [paragraph, code])
        self.assertTrue(all(c.token_count <= 22 for c in chunks))

    def test_table_preserves_headers_spans_and_note_neighbor_links(self):
        rows = ((TableCell("Column", True, colspan=2),),
                (TableCell("replay_lag", rowspan=2), TableCell("NULL")))
        table = block("Column Type\nreplay_lag interval\nNULL lag meaning preserved", "table", rows=rows)
        note_path = ("Indexes", "Note")
        chunks = self.chunk(block("Table caption"), table,
                            block("Note", "heading", note_path, "NOTE"),
                            block("NULL is not zero lag.", path=note_path, anchor="NOTE"))
        self.assertEqual(chunks[0].blocks[1], table)
        self.assertEqual(chunks[0].blocks[1].table_rows, rows)
        self.assertEqual(chunks[0].next_chunk_id, chunks[1].chunk_id)
        self.assertEqual(chunks[1].previous_chunk_id, chunks[0].chunk_id)
        self.assertEqual(chunks[1].heading_path, note_path)
        self.assertEqual(chunks[1].block_indices, (4,))
        self.assertIsNone(chunks[0].previous_chunk_id)
        self.assertIsNone(chunks[-1].next_chunk_id)

    def test_headings_and_changed_or_restored_heading_paths_end_groups(self):
        root, child = ("Root",), ("Root", "Child")
        blocks = (block("Root", "heading", root), block("a", path=root),
                  block("b", path=child), block("c", path=root),
                  block("Root", "heading", root), block("d", path=root))
        chunks = self.chunk(*blocks)
        self.assertEqual([c.block_indices for c in chunks], [(2,), (3,), (4,), (6,)])
        self.assertEqual([c.heading_path for c in chunks], [root, child, root, root])
        self.assertFalse(any(b.kind == "heading" for c in chunks for b in c.blocks))

    def test_empty_and_heading_only_documents_have_no_embedding_chunks(self):
        self.assertEqual(self.chunk(), ())
        self.assertEqual(self.chunk(block("Indexes", "heading")), ())

    def test_complete_context_and_special_tokens_enforce_limit(self):
        code = block(" ".join(["sql"] * 20), "code")
        self.assertLessEqual(word_count(code.text), self.settings.max_tokens)
        with self.assertRaises(ChunkOverflowError) as caught:
            self.chunk(code)
        self.assertEqual(caught.exception.token_count, 24)
        self.assertEqual(caught.exception.max_tokens, 22)
        # Exact fit is allowed, including all context and special tokens.
        self.assertEqual(self.chunk(block(" ".join(["sql"] * 18), "code"))[0].token_count, 22)

    def test_oversized_block_of_any_kind_reports_position_without_mutation(self):
        for kind in ("paragraph", "code", "table"):
            with self.subTest(kind=kind):
                large = block(" ".join(["large"] * 30), kind)
                document = replace(self.document, blocks=(block("Small."), large))
                with self.assertRaises(ChunkOverflowError) as caught:
                    chunk_document(document, count_tokens=word_count, tokenizer=self.tokenizer,
                                   settings=self.settings)
                self.assertEqual(caught.exception.block_index, 2)
                self.assertEqual(caught.exception.source_id, document.source_id)
                self.assertEqual(caught.exception.snapshot_id, document.snapshot_id)
                self.assertEqual(caught.exception.kind, kind)
                self.assertEqual(document.blocks, (block("Small."), large))

    def test_combined_input_is_counted_instead_of_summing_block_counts(self):
        def nonadditive_count(text):
            return word_count(text) + (20 if "alpha\n\nbeta" in text else 0)

        chunks = self.chunk(block("alpha"), block("beta"), count_tokens=nonadditive_count)
        self.assertEqual([c.block_indices for c in chunks], [(1,), (2,)])

    def test_repeated_calls_preserve_all_metadata_and_deterministic_ids(self):
        document = replace(self.document, blocks=(block("First."), block("SELECT 1;", "code")))
        kwargs = dict(count_tokens=word_count, tokenizer=self.tokenizer, settings=self.settings)
        first = chunk_document(document, **kwargs)
        self.assertEqual(first, chunk_document(document, **kwargs))
        chunk = first[0]
        for key in ("source_id", "snapshot_id", "source_url", "source_sha256", "parser_version"):
            self.assertEqual(getattr(chunk, key), getattr(document, key))
        self.assertEqual(chunk.tokenizer, self.tokenizer)
        for changed in (replace(document, snapshot_id="snapshot-2"),
                        replace(document, source_id="OTHER-SOURCE"),
                        replace(document, parser_version="parser-v2"),
                        replace(document, source_sha256=sha256(b"changed").hexdigest()),
                        replace(document, blocks=(block("Changed."), document.blocks[1]))):
            self.assertNotEqual(chunk.chunk_id, chunk_document(changed, **kwargs)[0].chunk_id)

    def test_settings_and_tokenizer_identity_changes_produce_new_chunk_ids(self):
        original = self.chunk(block("Text."))[0].chunk_id
        for tokenizer in (replace(self.tokenizer, identifier="another-tokenizer"),
                          replace(self.tokenizer, revision="v2"),
                          replace(self.tokenizer, fingerprint="another-backend-setup")):
            self.assertNotEqual(original, self.chunk(block("Text."), tokenizer=tokenizer)[0].chunk_id)
        for settings in (replace(self.settings, target_tokens=13),
                         replace(self.settings, max_tokens=23),
                         replace(self.settings, document_prefix="document: ")):
            self.assertNotEqual(original, self.chunk(block("Text."), settings=settings)[0].chunk_id)

    def test_invalid_budgets_metadata_counter_and_blocks_fail_explicitly(self):
        for settings in (ChunkSettings(0, 22), ChunkSettings(23, 22),
                         ChunkSettings(12, True), ChunkSettings(12, 22.5),
                         ChunkSettings(12, 22, None)):
            with self.subTest(settings=settings), self.assertRaises(ChunkingError):
                self.chunk(block("Text."), settings=settings)
        for tokenizer in (replace(self.tokenizer, max_input_tokens=10),
                          replace(self.tokenizer, max_input_tokens=0),
                          replace(self.tokenizer, identifier=""),
                          replace(self.tokenizer, revision=""),
                          replace(self.tokenizer, fingerprint="")):
            with self.subTest(tokenizer=tokenizer), self.assertRaises(ChunkingError):
                self.chunk(block("Text."), tokenizer=tokenizer)
        for count in (0, -1, True, 1.5):
            with self.subTest(count=count), self.assertRaises(ChunkingError):
                self.chunk(block("Text."), count_tokens=lambda text: count)
        for invalid in (block(""), block("  "), block("Text", "unsupported"),
                        block("Text", path=("",)), block("Text", path=["Indexes"])):
            with self.subTest(block=invalid), self.assertRaises(ChunkingError):
                self.chunk(invalid)


if __name__ == "__main__":
    unittest.main()
