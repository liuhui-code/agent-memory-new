# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.agent_memory_runtime import code_wiki_indexing as indexing
from tools.agent_memory_runtime.required_source_reads import RequiredSourceReadError, read_source_bytes
from tools.agent_memory_runtime.storage import resolve_project, ensure_initialized, connect


class RequiredSourceReadsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name) / 'source'
        root.mkdir()
        self.leaf = root / 'Leaf.ts'
        self.caller = root / 'Caller.ts'
        self.leaf.write_text('export class Leaf {\n step(): string { return "before"; }\n}\n')
        self.caller.write_text('import { Leaf } from "./Leaf";\nexport class Caller {\n run(): string { return new Leaf().step(); }\n}\n')
        self.project = resolve_project(str(root), str(Path(self.temp.name) / 'memory'))
        ensure_initialized(self.project)
        indexing.write_wiki_index(self.project, [self.leaf, self.caller], True)
        self.before = self.dump()
        self.leaf.write_text(self.leaf.read_text().replace('before', 'after'))

    def tearDown(self):
        self.temp.cleanup()

    def dump(self):
        with connect(self.project) as conn:
            return '\n'.join(conn.iterdump())

    def test_missing_undeclared_dependent_refuses_before_tracking(self):
        self.caller.unlink()
        with patch.object(indexing, 'begin_memory_edge_tracking') as tracking:
            with self.assertRaises(RequiredSourceReadError):
                indexing.write_wiki_index(self.project, [self.leaf])
            tracking.assert_not_called()
        self.assertEqual(self.before, self.dump())
        with self.assertRaises(FileNotFoundError):
            read_source_bytes(self.caller)  # The writer policy was reset after refusal.

    def test_changed_undeclared_dependent_refuses_before_tracking(self):
        self.caller.write_text(self.caller.read_text().replace('new Leaf().step()', '"changed"'))
        with patch.object(indexing, 'begin_memory_edge_tracking') as tracking:
            with self.assertRaisesRegex(RequiredSourceReadError, 'changed outside declared refresh'):
                indexing.write_wiki_index(self.project, [self.leaf])
            tracking.assert_not_called()
        self.assertEqual(self.before, self.dump())

    def test_missing_after_preflight_rolls_back_actual_rebuild(self):
        original = indexing.rebuild_code_memory_edges
        def raced(*args, **kwargs):
            self.caller.unlink()
            return original(*args, **kwargs)
        with patch.object(indexing, 'rebuild_code_memory_edges', side_effect=raced):
            with self.assertRaises(RequiredSourceReadError):
                indexing.write_wiki_index(self.project, [self.leaf])
        self.assertEqual(self.before, self.dump())

    def test_changed_after_preflight_rolls_back_actual_rebuild(self):
        original = indexing.rebuild_code_memory_edges
        def raced(*args, **kwargs):
            self.caller.write_text(self.caller.read_text().replace('new Leaf().step()', '"changed"'))
            return original(*args, **kwargs)
        with patch.object(indexing, 'rebuild_code_memory_edges', side_effect=raced):
            with self.assertRaises(RequiredSourceReadError):
                indexing.write_wiki_index(self.project, [self.leaf])
        self.assertEqual(self.before, self.dump())

    def test_io_error_during_actual_semantic_read_rolls_back(self):
        original = Path.read_bytes
        reads = 0
        def raced(path):
            nonlocal reads
            if path == self.caller:
                reads += 1
                if reads > 1:
                    raise PermissionError('controlled read error after successful probe')
            return original(path)
        with patch.object(Path, 'read_bytes', raced):
            with self.assertRaises(RequiredSourceReadError):
                indexing.write_wiki_index(self.project, [self.leaf])
        self.assertGreater(reads, 1)
        self.assertEqual(self.before, self.dump())

    def test_explicit_retired_missing_source_allowed(self):
        self.caller.unlink()
        indexing.write_wiki_index(self.project, [self.leaf], retired_relative_files=['Caller.ts'])
        with connect(self.project) as conn:
            self.assertEqual(['Leaf.ts'], [row[0] for row in conn.execute('SELECT file_path FROM code_files')])

    def test_full_replace_can_remove_missing_source(self):
        self.caller.unlink()
        indexing.write_wiki_index(self.project, [self.leaf], replace=True)
        with connect(self.project) as conn:
            self.assertEqual(['Leaf.ts'], [row[0] for row in conn.execute('SELECT file_path FROM code_files')])

    def test_explicitly_refreshed_changed_dependent_allowed(self):
        self.caller.write_text(self.caller.read_text().replace('new Leaf().step()', '"changed"'))
        indexing.write_wiki_index(self.project, [self.leaf, self.caller])
        with connect(self.project) as conn:
            row = conn.execute("SELECT source_digest,index_generation FROM code_files WHERE file_path='Caller.ts'").fetchone()
            self.assertEqual(indexing.file_sha256(self.caller), row[0])
            for symbol in conn.execute("SELECT source_digest,index_generation FROM code_symbols WHERE file_path='Caller.ts'"):
                self.assertEqual(tuple(row), tuple(symbol))

    def test_retargeted_symlink_after_probe_refuses_even_matching_bytes(self):
        for changed in (False, True):
            with self.subTest(changed=changed):
                original = indexing.rebuild_code_memory_edges
                content = self.caller.read_text()
                def raced(*args, **kwargs):
                    alternate = self.caller.parent / 'alternate.txt'
                    alternate.write_text(content.replace('new Leaf().step()', '"changed"') if changed else content)
                    self.caller.unlink()
                    self.caller.symlink_to(alternate)
                    return original(*args, **kwargs)
                with patch.object(indexing, 'rebuild_code_memory_edges', side_effect=raced):
                    with self.assertRaisesRegex(RequiredSourceReadError, 'target changed'):
                        indexing.write_wiki_index(self.project, [self.leaf])
                self.assertEqual(self.before, self.dump())
                self.caller.unlink()
                self.caller.write_text(content)

    def test_resolved_provider_path_cannot_bypass_required_alias(self):
        from tools.agent_memory_runtime.required_source_reads import required_source_reads
        from tools.agent_memory_runtime.semantic_provider_protocol import build_provider_request
        from tools.agent_memory_runtime.semantic_symbol_evidence import safe_source_path
        with required_source_reads() as required:
            required[self.caller.absolute()] = (indexing.file_sha256(self.caller), self.caller.resolve())
            alternate = self.caller.parent / 'alternate.txt'
            alternate.write_text('changed')
            self.caller.unlink()
            self.caller.symlink_to(alternate)
            with self.assertRaisesRegex(RequiredSourceReadError, 'target changed'):
                build_provider_request(self.project, 'TypeScript', [self.caller])
            with self.assertRaisesRegex(RequiredSourceReadError, 'target changed'):
                safe_source_path(self.project, 'Caller.ts')
