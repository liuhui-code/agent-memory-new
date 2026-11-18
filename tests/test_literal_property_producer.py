# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Finite lexical source facts; SQLite component tests, no public CLI claims."""
import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.agent_memory_runtime.ecma_literal_property_path import literal_property_paths
from tools.agent_memory_runtime.semantic_adapters import TypeScriptSemanticAdapter
from tools.agent_memory_runtime.semantic_index import enrich_code_symbols
from tools.agent_memory_runtime.storage import resolve_project
from tools.agent_memory_runtime.storage_schema import create_schema
from tools.agent_memory_runtime.storage_migrations import migrate_schema

SOURCE = "export const OperationPlan = {\n upload: {\n  title: 'Upload draft',\n  execute: () => {\n   sendDraft()\n  }\n },\n discard: {\n  title: 'Discard draft',\n  execute: () => {\n   clearDraft()\n  }\n }\n}\n"
CONTROLS = {'flat': 'export const A = {\n run: () => { work() }\n}\n', 'unique_nested': 'export const A = {\n first: {\n  run: () => { work() }\n }\n}\n', 'duplicate': 'export const A = {\n first: {\n  run: () => { work() }\n },\n first: {\n  run: () => { other() }\n }\n}\n', 'spread': 'export const A = {\n ...other,\n first: {\n  run: () => { work() }\n }\n}\n', 'computed': 'export const A = {\n [key]: {\n  run: () => { work() }\n }\n}\n', 'alias': 'export const A = {\n first: other\n}\n', 'array': 'export const A = {\n first: [\n  { run: () => { work() } }\n ]\n}\n', 'same_line': 'export const A = { first: { run: () => { work() } }, second: { run: () => { other() } } }\n', 'fake_text': "export const A = {\n text: 'first: { run: () => { work() } }'\n}\n", 'comment': 'export const A = {\n // first: { run: () => { work() } }\n}\n', 'malformed': 'export const A = {\n first: {\n  run: () => { work() }\n', 'collision': 'export const orderingguard = {\n statewrite: {\n  run: () => { work() }\n }\n}\n'}


class LiteralPropertyProducerTests(unittest.TestCase):
    def test_original_source_mapping_and_legacy_payload(self):
        self.assertEqual(hashlib.sha256(SOURCE.encode()).hexdigest(),
                         '95136eb4d2d7d1d3bb4337efa27dd9b3d60623d4627daab542a4df51b9586f0d')
        self.assertEqual(literal_property_paths(SOURCE), {
            (4, 6, 'execute'): 'OperationPlan.upload.execute',
            (10, 12, 'execute'): 'OperationPlan.discard.execute'})
        self.assertEqual(literal_property_paths(SOURCE.replace('\n', '\r\n')),
                         literal_property_paths(SOURCE))
        self.assertEqual(literal_property_paths(CONTROLS['flat']), {})
        self.assertEqual(literal_property_paths(CONTROLS['unique_nested']),
                         {(3, 3, 'run'): 'A.first.run'})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); path = root / 'OperationPlan.ts'; path.write_text(SOURCE)
            project = resolve_project(root, root / 'home')
            batch = TypeScriptSemanticAdapter().index(project, [path])
            callbacks = [e for e in batch.entities if e.name == 'execute']
            self.assertEqual([e.qualified_name for e in callbacks],
                             ['OperationPlan.execute@4', 'OperationPlan.execute@10'])
            self.assertEqual([e.owner_name for e in callbacks], ['OperationPlan'] * 2)
            conn = self.database(project, callbacks)
            self.assertEqual([tuple(r) for r in conn.execute('SELECT start_line,end_line,symbol_key FROM code_symbols')], [(None,None,None)] * len(callbacks))
            before = batch.to_dict()
            with patch('tools.agent_memory_runtime.ecma_literal_property_path.literal_property_paths', return_value={}):
                enrich_code_symbols(conn, project, batch)
            old = [dict(r) for r in conn.execute('SELECT * FROM code_symbols ORDER BY id')]
            conn.execute('UPDATE code_symbols SET symbol_key=NULL,qualified_name=NULL,signature=NULL,start_line=NULL,end_line=NULL,semantic_adapter=NULL')
            enrich_code_symbols(conn, project, batch)
            new = [dict(r) for r in conn.execute('SELECT * FROM code_symbols ORDER BY id')]
            self.assertEqual(batch.to_dict(), before)
            self.assertEqual([r.pop('literal_property_path') for r in new],
                             ['OperationPlan.upload.execute', 'OperationPlan.discard.execute'])
            for row in old: row.pop('literal_property_path')
            self.assertEqual(new, old)
            enrich_code_symbols(conn, project, batch)
            self.assertEqual([r[0] for r in conn.execute('SELECT literal_property_path FROM code_symbols ORDER BY id')], ['OperationPlan.upload.execute','OperationPlan.discard.execute'])
            conn.close()

    def test_unsupported_syntax_declines_without_aliases(self):
        for name in ('duplicate', 'spread', 'computed', 'alias', 'array',
                     'same_line', 'fake_text', 'comment', 'malformed'):
            with self.subTest(name=name):
                self.assertEqual(literal_property_paths(CONTROLS[name]), {})
        collision = CONTROLS['collision']
        self.assertEqual(literal_property_paths(collision),
                         {(3, 3, 'run'): 'orderingguard.statewrite.run'})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); path = root / 'Collision.ts'; path.write_text(collision)
            project = resolve_project(root, root / 'home')
            batch = TypeScriptSemanticAdapter().index(project, [path])
            callbacks = [e for e in batch.entities if e.name == 'run']
            conn = self.database(project, callbacks)
            before = batch.to_dict()
            with patch('tools.agent_memory_runtime.ecma_literal_property_path.literal_property_paths', return_value={}):
                enrich_code_symbols(conn, project, batch)
            old = [dict(r) for r in conn.execute('SELECT * FROM code_symbols ORDER BY id')]
            enrich_code_symbols(conn, project, batch)
            new = [dict(r) for r in conn.execute('SELECT * FROM code_symbols ORDER BY id')]
            self.assertEqual(batch.to_dict(), before)
            self.assertEqual([r.pop('literal_property_path') for r in new],
                             ['orderingguard.statewrite.run'])
            for row in old: row.pop('literal_property_path')
            # Entire prior row projection includes body/string/roles/owner/key.
            self.assertEqual(new, old)
            conn.close()
        self.assertEqual(literal_property_paths(SOURCE.replace("'Upload draft'", '`text ${call()}`')), {})

    def test_fixed_scanner_limits(self):
        valid = CONTROLS['unique_nested']
        self.assertTrue(literal_property_paths(valid + ' ' * (65536 - len(valid))))
        self.assertEqual(literal_property_paths(valid + ' ' * (65537 - len(valid))), {})
        for length in (64, 65):
            text = valid.replace('first', 'x' * length)
            self.assertEqual(bool(literal_property_paths(text)), length == 64)
        for count in (255, 256):
            # Root scalar entries plus nested object and callback: count+2.
            text = valid.replace(' first:', ''.join(f' p{i}: 0,\n' for i in range(count - 2)) + ' first:')
            self.assertTrue(literal_property_paths(text))
        too_many = valid.replace(' first:', ''.join(f' p{i}: 0,\n' for i in range(255)) + ' first:')
        self.assertEqual(literal_property_paths(too_many), {})
        for inner in (6, 7):
            text = 'const A = {\n' + ''.join(f'p{i}: {{\n' for i in range(inner))
            text += 'run: () => { work() }\n' + '}\n' * (inner + 1)
            self.assertEqual(bool(literal_property_paths(text)), inner == 6)

    def test_migration_relearn_and_mapping_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); path = root / 'OperationPlan.ts'; path.write_text(SOURCE)
            project = resolve_project(root, root / 'home')
            batch = TypeScriptSemanticAdapter().index(project, [path])
            callbacks = [e for e in batch.entities if e.name == 'execute']
            conn = self.database(project, callbacks)
            conn.execute('ALTER TABLE code_symbols DROP COLUMN literal_property_path')
            migrate_schema(conn); migrate_schema(conn)
            self.assertEqual([r[0] for r in conn.execute('SELECT literal_property_path FROM code_symbols')], [None, None])
            enrich_code_symbols(conn, project, batch)
            self.assertEqual([r[0] for r in conn.execute('SELECT literal_property_path FROM code_symbols ORDER BY id')],
                             ['OperationPlan.upload.execute', 'OperationPlan.discard.execute'])
            path.write_text(SOURCE.replace(' upload: {', ' ...unknown,\n upload: {'))
            changed = TypeScriptSemanticAdapter().index(project, [path])
            enrich_code_symbols(conn, project, changed)
            self.assertEqual([r[0] for r in conn.execute('SELECT literal_property_path FROM code_symbols')], [None, None])
            path.write_text(SOURCE)
            for mutation in (
                "UPDATE code_symbols SET start_line=4,end_line=6 WHERE id=1",
                "UPDATE code_symbols SET start_line=4 WHERE id=1",
                "UPDATE code_symbols SET source_digest='wrong' WHERE id=1",
                "UPDATE code_symbols SET index_generation=2 WHERE id=1",
                "UPDATE code_symbols SET symbol_key='wrong' WHERE id=1",
                "DELETE FROM code_symbols WHERE id=2",
                "INSERT INTO code_symbols(project_id,file_path,symbol,symbol_type,source_digest,index_generation,updated_at) SELECT project_id,file_path,symbol,symbol_type,source_digest,index_generation,updated_at FROM code_symbols WHERE id=1",
            ):
                with self.subTest(mutation=mutation):
                    trial = self.database(project, callbacks)
                    trial.execute(mutation)
                    enrich_code_symbols(trial, project, batch)
                    self.assertTrue(all(r[0] is None for r in trial.execute('SELECT literal_property_path FROM code_symbols')))
                    trial.close()
            # Deliberately reversed original rows: never attach another callback's spelling.
            conn.execute('UPDATE code_symbols SET start_line=CASE id WHEN 1 THEN 10 ELSE 4 END, end_line=CASE id WHEN 1 THEN 12 ELSE 6 END')
            enrich_code_symbols(conn, project, batch)
            self.assertEqual([r[0] for r in conn.execute('SELECT literal_property_path FROM code_symbols')], [None, None])
            # Same range duplicates cannot acquire a path even when legacy mapping continues.
            conn.execute('UPDATE code_symbols SET start_line=4,end_line=6')
            enrich_code_symbols(conn, project, batch)
            self.assertEqual([r[0] for r in conn.execute('SELECT literal_property_path FROM code_symbols')], [None, None])
            conn.close()

    def database(self, project, callbacks):
        conn = sqlite3.connect(':memory:'); conn.row_factory = sqlite3.Row
        create_schema(conn)
        for entity in callbacks:
            conn.execute('INSERT INTO code_symbols(project_id,file_path,symbol,symbol_type,summary,calls,source_digest,index_generation,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',
                         (project.project_id, entity.file_path, entity.name, entity.kind,
                          'fixture summary', '', hashlib.sha256((project.root / entity.file_path).read_bytes()).hexdigest(),
                          1, 'fixed-component-clock'))
        return conn
