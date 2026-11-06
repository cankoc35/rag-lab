"""Offline parsing checks; synthetic DocBook fixture, no local snapshot dependency."""

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import asdict, replace
from hashlib import sha256
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from rag_workflow_lab.cli import main
from rag_workflow_lab.contracts import SourceSelection, SourceSnapshot
from rag_workflow_lab.ingestion.download import load_sources
from rag_workflow_lab.ingestion.parse import PARSER_VERSION, SourceParseError, parse_html, parse_snapshot


ROOT = Path(__file__).resolve().parents[2]
HTML = (ROOT / 'tests/fixtures/postgresql_docbook.html').read_bytes()
SECTION = 'MONITORING-PG-STAT-REPLICATION-VIEW'


class ParseSourceTests(unittest.TestCase):
    def setUp(self):
        self.source = load_sources(ROOT / 'data/corpus/sources.json')[0]
        self.snapshot = SourceSnapshot(
            snapshot_id='PG-EXPLAIN-fixture', source=self.source,
            downloaded_at='2026-11-05T00:00:00Z', resolved_url=self.source.url,
            http_status=200, content_type='text/html', charset='utf-8',
            size_bytes=len(HTML), sha256=sha256(HTML).hexdigest(), local_path='source.html',
        )
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.folder = Path(self.directory.name)
        self.manifest = self.folder / 'manifest.json'
        self.save_snapshot()
        network = patch('socket.create_connection', side_effect=AssertionError('Unexpected network access'))
        network.start()
        self.addCleanup(network.stop)

    def save_snapshot(self, *, content=HTML, snapshot=None):
        snapshot = snapshot or self.snapshot
        (self.folder / 'source.html').write_bytes(content)
        self.manifest.write_text(json.dumps({'schema_version': 1, 'snapshot': asdict(snapshot)}), encoding='utf-8')

    def parse_content(self, content):
        return parse_html(content, replace(self.snapshot, size_bytes=len(content), sha256=sha256(content).hexdigest()))

    def test_page_preserves_content_order_and_removes_chrome(self):
        document = parse_html(HTML, self.snapshot)
        text = '\n'.join(b.text for b in document.blocks)
        for noise in ('SITE_NOISE', 'SEARCH_NOISE', 'NAV_NOISE', 'TOC_NOISE', 'SCRIPT_NOISE', 'CSS_NOISE', 'HIDDEN_NOISE', 'FOOTER_NOISE'):
            self.assertNotIn(noise, text)
        self.assertNotIn('#', document.blocks[0].text)
        self.assertIn('Keep inline_name and meaning together & readable.', text)
        self.assertIn('First list item.', text)
        self.assertIn('Second item.', text)
        self.assertLess(text.index('Query example'), text.index('Replication columns'))
        self.assertEqual(document.parser_version, PARSER_VERSION)
        self.assertEqual(document.source_id, self.source.source_id)
        self.assertEqual(document.snapshot_id, self.snapshot.snapshot_id)
        self.assertEqual(document.source_url, self.source.url)
        self.assertEqual(document.source_sha256, self.snapshot.sha256)

    def test_sql_newlines_indentation_and_entities_are_preserved(self):
        code = next(b for b in parse_html(HTML, self.snapshot).blocks if b.kind == 'code')
        self.assertEqual(code.text, 'EXPLAIN SELECT *\n    FROM orders\n    WHERE amount < 10 AND enabled = TRUE;')
        self.assertEqual(code.anchor, 'FIRST')
        self.assertEqual(code.heading_path, ('1. Fixture SQL', '1.1. Query example'))

    def test_heading_context_is_restored_after_sections_and_notes(self):
        blocks = parse_html(HTML, self.snapshot).blocks
        parent = next(b for b in blocks if b.text == 'Parent section after child.')
        self.assertEqual(parent.heading_path, ('1. Fixture SQL',))
        note = next(b for b in blocks if b.text == 'NULL is not proof of zero lag.')
        self.assertEqual(note.heading_path, ('1. Fixture SQL', '1.2. pg_stat_replication', 'Note'))
        after = next(b for b in blocks if b.text == 'Selected section after note.')
        self.assertEqual(after.heading_path, ('1. Fixture SQL', '1.2. pg_stat_replication'))
        self.assertEqual(after.anchor, SECTION)

    def test_table_cells_header_spans_and_paragraph_boundaries_are_preserved(self):
        table = next(b for b in parse_html(HTML, self.snapshot).blocks if b.kind == 'table')
        self.assertEqual(table.anchor, 'REPLICATION-TABLE')
        self.assertEqual(len(table.table_rows), 3)
        self.assertTrue(table.table_rows[0][0].is_header)
        self.assertEqual(table.table_rows[0][0].colspan, 2)
        self.assertEqual(table.table_rows[1][0].rowspan, 2)
        self.assertEqual(table.table_rows[1][0].text, 'replay_lag interval\nReplay delay.')
        self.assertEqual(table.table_rows[2][0].text, 'NULL')
        # A consumed table's cell text must not also be emitted as standalone paragraphs.
        self.assertFalse(any(b.kind == 'paragraph' and b.text == 'Replay delay.' for b in parse_html(HTML, self.snapshot).blocks))

    def test_section_scope_keeps_table_and_following_null_notes_only(self):
        source = replace(self.source, selection=SourceSelection('sections', (SECTION,)))
        document = parse_html(HTML, replace(self.snapshot, source=source))
        text = '\n'.join(b.text for b in document.blocks)
        self.assertIn('NULL is not proof of zero lag.', text)
        self.assertIn('Selected section after note.', text)
        self.assertNotIn('EXPLAIN SELECT', text)
        self.assertNotIn('OTHER_SECTION_NOISE', text)
        self.assertNotIn('Parent section after child.', text)
        self.assertEqual(document.blocks[0].heading_path, ('1. Fixture SQL', '1.2. pg_stat_replication'))
        self.assertTrue(all(b.heading_path[:2] == document.blocks[0].heading_path for b in document.blocks))

    def test_multiple_sections_follow_document_order(self):
        source = replace(self.source, selection=SourceSelection('sections', (SECTION, 'FIRST')))
        document = parse_html(HTML, replace(self.snapshot, source=source))
        self.assertEqual(document.blocks[0].anchor, 'FIRST')
        self.assertNotIn('OTHER_SECTION_NOISE', '\n'.join(b.text for b in document.blocks))

    def test_missing_duplicate_overlapping_or_invalid_scope_fails(self):
        for selection in (SourceSelection('sections', ('MISSING',)), SourceSelection('sections', (SECTION, SECTION)), SourceSelection('sections', ('ROOT', SECTION)), SourceSelection('sections'), SourceSelection('page', (SECTION,)), SourceSelection('unknown')):
            with self.subTest(selection=selection), self.assertRaises(SourceParseError):
                parse_html(HTML, replace(self.snapshot, source=replace(self.source, selection=selection)))
        for extra in (b'<div class="sect2" id="FIRST"><h3>Duplicate</h3></div>', b''):
            content = HTML.replace(b'<div class="sect2" id="OTHER">', extra + b'<div class="sect2" id="OTHER">')
            target = 'FIRST' if extra else 'REPLICATION-TABLE'
            snapshot = replace(self.snapshot, source=replace(self.source, selection=SourceSelection('sections', (target,))), size_bytes=len(content), sha256=sha256(content).hexdigest())
            with self.subTest(target=target), self.assertRaises(SourceParseError):
                parse_html(content, snapshot)

    def test_excluded_section_cannot_be_selected_through_its_id(self):
        content = HTML.replace(b'<div class="sect2" id="FIRST">', b'<div class="sect2 toc" id="FIRST">')
        snapshot = replace(self.snapshot, source=replace(self.source, selection=SourceSelection('sections', ('FIRST',))), size_bytes=len(content), sha256=sha256(content).hexdigest())
        with self.assertRaises(SourceParseError):
            parse_html(content, snapshot)

    def test_missing_body_empty_scope_and_unclosed_html_fail(self):
        for content in (b'<html><body><h2>No docContent</h2></body></html>', b'<div id="docContent"></div>', b'<div id="docContent"><h2>Unclosed</h2>', b'<div id="docContent"><h2>Mismatch</div></h2>'):
            with self.subTest(content=content), self.assertRaises(SourceParseError):
                self.parse_content(content)

    def test_size_hash_and_encoding_must_match_the_saved_bytes(self):
        for snapshot in (replace(self.snapshot, size_bytes=len(HTML) + 1), replace(self.snapshot, sha256='0' * 64), replace(self.snapshot, charset='unknown-encoding'), replace(self.snapshot, snapshot_id='')):
            with self.subTest(snapshot=snapshot), self.assertRaises(SourceParseError):
                parse_html(HTML, snapshot)
        with self.assertRaisesRegex(SourceParseError, 'decode'):
            self.parse_content(HTML.replace(b'Keep', b'\xffKeep'))

    def test_snapshot_loading_is_deterministic_and_preserves_inputs(self):
        before = {p.name: p.read_bytes() for p in self.folder.iterdir()}
        first = parse_snapshot(self.manifest, self.source)
        self.assertEqual(first, parse_snapshot(self.manifest, self.source))
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.folder.iterdir()})

    def test_snapshot_rejects_mismatched_source_and_modified_html(self):
        with self.assertRaisesRegex(SourceParseError, 'source differs'):
            parse_snapshot(self.manifest, replace(self.source, selection=SourceSelection('sections', (SECTION,))))
        (self.folder / 'source.html').write_bytes(HTML.replace(b'Keep', b'Lose'))
        with self.assertRaisesRegex(SourceParseError, 'SHA-256'):
            parse_snapshot(self.manifest, self.source)

    def test_snapshot_rejects_missing_or_malformed_metadata(self):
        for payload in ({'schema_version': True}, {'schema_version': 2}, [], {'schema_version': 1, 'snapshot': {'source': asdict(self.source)}}):
            self.manifest.write_text(json.dumps(payload), encoding='utf-8')
            with self.subTest(payload=payload), self.assertRaises(SourceParseError):
                parse_snapshot(self.manifest, self.source)
        self.manifest.write_text('{invalid', encoding='utf-8')
        with self.assertRaises(SourceParseError):
            parse_snapshot(self.manifest, self.source)
        with self.assertRaises(SourceParseError):
            parse_snapshot(self.folder / 'missing.json', self.source)

    def test_snapshot_rejects_html_path_escape_and_failed_responses(self):
        for local in ('../source.html', '/tmp/source.html', '', '.'):
            self.save_snapshot(snapshot=replace(self.snapshot, local_path=local))
            with self.subTest(local=local), self.assertRaises(SourceParseError):
                parse_snapshot(self.manifest, self.source)
        for changes in ({'http_status': 404}, {'content_type': 'text/plain'}, {'resolved_url': 'https://example.com/'}):
            self.save_snapshot(snapshot=replace(self.snapshot, **changes))
            with self.subTest(changes=changes), self.assertRaises(SourceParseError):
                parse_snapshot(self.manifest, self.source)
        with TemporaryDirectory() as other:
            outside = Path(other) / 'outside.html'
            outside.write_bytes(HTML)
            (self.folder / 'link.html').symlink_to(outside)
            self.save_snapshot(snapshot=replace(self.snapshot, local_path='link.html'))
            with self.assertRaises(SourceParseError):
                parse_snapshot(self.manifest, self.source)

    def test_invalid_or_nested_content_tables_fail_explicitly(self):
        for replacement in (b'<table><tr><td rowspan="oops">bad</td></tr></table>', b'<table><tr><td colspan="0">bad</td></tr></table>', b'<table><tr><td><table><tr><td>nested</td></tr></table></td></tr></table>', b'<table></table>'):
            content = HTML.replace(b'<p>Parent section after child.</p>', replacement)
            with self.subTest(replacement=replacement), self.assertRaises(SourceParseError):
                self.parse_content(content)

    def test_cli_parses_saved_snapshot_and_reports_local_errors(self):
        args = ['parse-source', '--config', str(ROOT / 'configs/pilot.toml'), '--source-id', self.source.source_id, '--manifest', str(self.manifest)]
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(args), 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload['schema_version'], 1)
        self.assertEqual(payload['document']['source_id'], self.source.source_id)
        self.assertTrue(payload['document']['blocks'])
        self.manifest.write_text('{}', encoding='utf-8')
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            main(args)
        self.assertEqual(error.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
