"""Development controls for source authentication, not CLI acceptance."""
import copy
import hashlib
from pathlib import Path
import tempfile
import sqlite3
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from tools.agent_memory_runtime import query_sql_slot_snapshot as s


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.project = SimpleNamespace(root=self.root, project_id='development')
        self.files, self.rows, self.pool = [], [], []
        for i, name in enumerate(('Main.ets', 'Other.ets'), 1):
            source = 'export class Owner%d {\n  findRows() { return [] }\n}\n' % i
            (self.root / name).write_text(source)
            digest = hashlib.sha256(source.encode()).hexdigest()
            f = dict(id=i, project_id='development', file_path=name, language='ArkTS',
                     source_digest=digest, index_generation=1)
            r = dict(f, symbol='findRows', symbol_key='symbol:'+name,
                     qualified_name='Owner%d.findRows'%i, start_line=2, end_line=2,
                     owner_name='Owner%d'%i, owner_kind='service', semantic_adapter='arkts-static@1.2',
                     evidence_class='static', symbol_type='function')
            self.files.append(f); self.rows.append(r)
            self.pool.append(dict(r, kind='symbol'))
        self.mock = patch.object(s, 'project_rows', side_effect=lambda *_: (copy.deepcopy(self.files), copy.deepcopy(self.rows)))
        self.mock.start(); self.addCleanup(self.mock.stop)

    def load(self): return s.load_scope(self.project, self.pool)

    def test_method_only_scope_and_typed_equal_id(self):
        self.pool.append(dict(self.files[0], kind='file'))
        scope = self.load()
        self.assertIsNotNone(scope)
        self.assertTrue(s.current_scope(scope))
        owner = dict(symbol='Owner1', owner_kind='service')
        decl = dict(name='findRows', span=dict(start_line=2, end_line=2))
        self.assertEqual(s.method_root(scope, 'Main.ets', owner, decl)['id'], 1)
        scope['pool'] = [r for r in scope['pool'] if r['kind']=='file' or r['id'] != 1]
        self.assertIsNone(s.method_root(scope, 'Main.ets', owner, decl))

    def test_identity_conflicts(self):
        for key, value in [('project_id','wrong'), ('source_digest','0'*64), ('index_generation',2),
                           ('semantic_adapter','unknown@1'), ('start_line',3), ('symbol_key','wrong')]:
            with self.subTest(key=key):
                old = self.pool[0][key]; self.pool[0][key] = value
                self.assertIsNone(self.load()); self.pool[0][key] = old
        duplicate = dict(self.pool[0], end_line=3)
        self.pool.append(duplicate); self.assertIsNone(self.load())

    def test_whole_scope_paths_before_filter(self):
        self.pool += [dict(self.pool[0], file_path=f'Path{i}.ets', id=i+20) for i in range(11)]
        self.assertIsNone(self.load())

    def test_all_scoped_bytes_not_only_output(self):
        scope = self.load()
        for appended in ('\n', 'export class New { @State rows: string[] = [] }\n'):
            path=self.root/'Other.ets'; before=path.read_bytes();path.write_bytes(before+appended.encode())
            self.assertFalse(s.current_scope(scope));path.write_bytes(before)
        self.assertTrue(s.current_scope(scope))

    def test_db_only_changes(self):
        scope=self.load()
        for key, value in [('symbol_key','changed'),('index_generation',2),('owner_name','Changed')]:
            before=self.rows[1][key];self.rows[1][key]=value
            self.assertFalse(s.current_scope(scope));self.rows[1][key]=before
        self.assertTrue(s.current_scope(scope))

    def test_source_size_escape_extension_unknown(self):
        path=self.root/'Main.ets';path.write_bytes(b' '* (s.MAX_SOURCE+1))
        self.assertIsNone(self.load())
        for name in ('../Other.ets','/tmp/Other.ets','Main.ts','./Main.ets'):
            with self.assertRaises(ValueError):s.source_bytes(self.root,name)

    def test_real_sql_fetches_same_key_alias_outside_scope(self):
        self.mock.stop()
        conn=sqlite3.connect(':memory:');conn.row_factory=sqlite3.Row
        self.addCleanup(conn.close)
        for table,rows in [('code_files',self.files),('code_symbols',self.rows)]:
            keys=list(rows[0]);conn.execute('CREATE TABLE '+table+' ('+','.join(k+' '+('INTEGER' if type(rows[0][k]) is int else 'TEXT') for k in keys)+')')
            for row in rows:conn.execute('INSERT INTO '+table+' VALUES ('+','.join('?' for _ in keys)+')',[row[k] for k in keys])
        with patch.object(s,'connect',return_value=conn):
            scope=self.load();self.assertIsNotNone(scope)
            alias=dict(self.rows[0],id=101,file_path='Outside.ets')
            keys=list(alias);conn.execute('INSERT INTO code_symbols VALUES ('+','.join('?' for _ in keys)+')',[alias[k] for k in keys])
            self.assertIsNone(self.load())
            self.assertFalse(s.current_scope(scope))
        self.mock.start()

    def test_database_read_failure_declines_optional_view(self):
        scope=self.load()
        with patch.object(s,'project_rows',side_effect=sqlite3.OperationalError('locked')):
            self.assertIsNone(self.load())
            self.assertFalse(s.current_scope(scope))

    def test_unsupported_pool_rows(self):
        self.pool.append({'kind':'unknown','file_path':'Main.ets'})
        self.assertIsNone(self.load())

if __name__ == '__main__': unittest.main()
