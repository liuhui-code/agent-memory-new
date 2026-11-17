"""Fresh source/DB unit cohorts; no frozen public or original query replay."""
from copy import deepcopy
import tempfile
import unittest
from unittest.mock import patch
from tests.command_table_test_support import prepare
from tools.agent_memory_runtime.storage import connect
from tools.agent_memory_runtime.query_ui_vertical_scope import vertical_frames

SOURCE = '''@Component
export struct InvoiceRows {
  @State values: string[] = []
  build() {
    List() {
      ForEach(this.values, (value: string) => {
        ListItem() { Text(value) }
      })
    }.listDirection(Axis.Vertical)
  }
}
'''


def pool_for(project):
    # Unit caller inventory is assembled from normal learned rows, not production recall.
    with connect(project) as db:
        rows = [dict(r, kind='symbol') for r in db.execute('SELECT * FROM code_symbols WHERE project_id=?', (project.project_id,))]
        rows += [dict(r, kind='file') for r in db.execute('SELECT * FROM code_files WHERE project_id=?', (project.project_id,))]
    return rows


class VerticalScope(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = prepare(self.tmp.name, sources={'Rows.ets': SOURCE})
        self.pool = pool_for(self.project)
    def tearDown(self): self.tmp.cleanup()
    def frames(self, pool=None): return vertical_frames(self.project, self.pool if pool is None else pool, 'invoice')
    def test_admitted_roots_and_metadata_snapshot(self):
        frames = self.frames(); self.assertEqual(len(frames), 1)
        f = frames[0]
        self.assertEqual(f['owner']['symbol'], 'InvoiceRows'); self.assertEqual(f['build']['symbol'], 'build')
        self.assertEqual(f['pool_paths'], ('Rows.ets',)); self.assertEqual(f['state']['generation'], 1)
        self.assertTrue(f['metadata']); self.assertIn(f['build'], f['members'])
        self.assertFalse(any(r['symbol'].startswith('ForEach') for r in f['members']))
    def test_missing_original_owner_build_file_roots(self):
        for kind, name in [('symbol', 'InvoiceRows'), ('symbol', 'build'), ('file', None)]:
            pool = [r for r in self.pool if not (r['kind'] == kind and (name is None or r['symbol'] == name))]
            self.assertLess(len(pool), len(self.pool)); self.assertIsNone(self.frames(pool))
    def test_corrupt_root_identity(self):
        for key, value in [('id', True), ('symbol_key', None), ('signature', 'wrong'), ('owner_kind', 'class'),
                           ('start_line', 1), ('index_generation', True), ('source_digest', '0'*64)]:
            pool = deepcopy(self.pool); next(r for r in pool if r.get('symbol') == 'build')[key] = value
            self.assertIsNone(self.frames(pool), key)
    def test_project_root_metadata_mismatch(self):
        with connect(self.project) as db:
            db.execute("UPDATE projects SET project_path=? WHERE project_id=?", (str(self.project.root/'other'), self.project.project_id))
        self.assertIsNone(self.frames())
    def test_generation_and_file_flags(self):
        with connect(self.project) as db: db.execute('UPDATE code_index_state SET generation=2')
        self.assertIsNone(self.frames())
        with connect(self.project) as db:
            db.execute('UPDATE code_index_state SET generation=1')
            db.execute("UPDATE code_files SET language='TypeScript'")
        self.assertIsNone(self.frames(pool_for(self.project)))
    def test_global_alias_across_unrecalled_path(self):
        with connect(self.project) as db:
            row = dict(db.execute("SELECT * FROM code_symbols WHERE symbol='build'").fetchone())
            row.pop('id'); row['file_path'] = 'Hidden.ets'
            db.execute('INSERT INTO code_symbols ('+','.join(row)+') VALUES ('+','.join('?' for _ in row)+')', list(row.values()))
        self.assertIsNone(self.frames())
    def test_unknown_matching_declaration_never_negative(self):
        for declaration in ('export class InvoiceHelper {}', 'export interface InvoiceHelper { value: string }',
                            'export function InvoiceHelper(): string { return "x"; }'):
            with self.subTest(declaration=declaration), tempfile.TemporaryDirectory() as directory:
                project = prepare(directory, sources={'Rows.ets': SOURCE+'\n'+declaration})
                pool = pool_for(project)
                self.assertIsNone(vertical_frames(project, pool, 'invoice'))
                # Removing the unsupported root from the admitted pool cannot hide its DB inventory.
                pool = [r for r in pool if r.get('symbol') != 'InvoiceHelper']
                self.assertIsNone(vertical_frames(project, pool, 'invoice'))
    def test_same_file_second_matching_build_requires_own_root(self):
        with tempfile.TemporaryDirectory() as directory:
            project = prepare(directory, sources={'Rows.ets': SOURCE+'\n'+SOURCE.replace('InvoiceRows', 'InvoiceArchive')})
            pool = pool_for(project)
            self.assertEqual(len(vertical_frames(project, pool, 'invoice')), 2)
            pool = [r for r in pool if not (r.get('owner_name') == 'InvoiceArchive' and r.get('symbol') == 'build')]
            self.assertIsNone(vertical_frames(project, pool, 'invoice'))
    def test_db_extra_member_drift_and_bad_ranges(self):
        before = self.frames()[0]['metadata']
        with connect(self.project) as db: db.execute("UPDATE code_symbols SET signature='changed' WHERE symbol='values'")
        self.assertNotEqual(self.frames(pool_for(self.project))[0]['metadata'], before)
        with connect(self.project) as db: db.execute("UPDATE code_symbols SET end_line=999 WHERE symbol='values'")
        self.assertIsNone(self.frames(pool_for(self.project)))
    def test_null_event_keys_are_not_global_aliases(self):
        with connect(self.project) as db:
            seed = dict(db.execute("SELECT * FROM code_symbols WHERE symbol='build'").fetchone())
            for name in ('notifyOne', 'notifyTwo'):
                row = dict(seed); row.pop('id')
                row.update(symbol=name, symbol_key=None, qualified_name=name, symbol_type='event', owner_name='', owner_kind='')
                db.execute('INSERT INTO code_symbols ('+','.join(row)+') VALUES ('+','.join('?' for _ in row)+')', list(row.values()))
        self.assertIsNotNone(self.frames(pool_for(self.project)))
    def test_same_subject_state_name_is_not_top_level_declaration(self):
        with tempfile.TemporaryDirectory() as directory:
            source = SOURCE.replace('values', 'invoiceValues')
            project = prepare(directory, sources={'Rows.ets': source})
            frames = vertical_frames(project, pool_for(project), 'invoice')
            self.assertEqual(len(frames), 1)
            self.assertIn('invoiceValues', {r['symbol'] for r in frames[0]['members']})
    def test_matching_frame_cap_in_one_file(self):
        with tempfile.TemporaryDirectory() as directory:
            source = '\n'.join(SOURCE.replace('InvoiceRows', 'InvoiceRows'+str(i)) for i in range(13))
            project = prepare(directory, sources={'Rows.ets': source})
            self.assertIsNone(vertical_frames(project, pool_for(project), 'invoice'))
    def test_nonmatching_pool_path_needs_current_file_metadata(self):
        helper='export class OtherHelper { answer(): string { return "ok"; } }'
        for fault in ('missing', 'generation', 'digest', 'language'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as directory:
                project=prepare(directory,sources={'Rows.ets':SOURCE,'Other.ts':helper})
                pool=pool_for(project)
                self.assertIsNotNone(vertical_frames(project,pool,'invoice'))
                with connect(project) as db:
                    if fault=='missing': db.execute("DELETE FROM code_files WHERE file_path='Other.ts'")
                    elif fault=='generation': db.execute("UPDATE code_files SET index_generation=2 WHERE file_path='Other.ts'")
                    elif fault=='digest': db.execute("UPDATE code_files SET source_digest='bad' WHERE file_path='Other.ts'")
                    else: db.execute("UPDATE code_files SET language='ArkTS' WHERE file_path='Other.ts'")
                # Keep actual original symbols; no stale file row masks the omitted-path check.
                pool=[r for r in pool if not(r['kind']=='file'and r['file_path']=='Other.ts')]
                self.assertTrue(any(r['file_path']=='Other.ts'for r in pool))
                self.assertIsNone(vertical_frames(project,pool,'invoice'))
    def test_scope_files_include_nonmatching_symbol_only_path(self):
        with tempfile.TemporaryDirectory() as directory:
            project=prepare(directory,sources={'Rows.ets':SOURCE,'Other.ts':'export class OtherHelper {}'})
            pool=pool_for(project)
            pool=[r for r in pool if not(r['kind']=='file'and r['file_path']=='Other.ts')]
            frames=vertical_frames(project,pool,'invoice')
            self.assertEqual([r['file_path']for r in frames[0]['scope_files']],['Other.ts','Rows.ets'])
            self.assertEqual({r['file_path']for r in frames[0]['scope_files']},set(frames[0]['pool_paths']))
    def test_one_explicit_read_transaction(self):
        from tools.agent_memory_runtime.query_ui_vertical_scope import connect as real_connect
        statements = []
        def traced(project):
            db = real_connect(project); db.set_trace_callback(statements.append); return db
        with patch('tools.agent_memory_runtime.query_ui_vertical_scope.connect', side_effect=traced): self.assertIsNotNone(self.frames())
        self.assertEqual(statements[0], 'BEGIN'); self.assertEqual(statements.count('BEGIN'), 1)
        self.assertEqual(statements[-1], 'COMMIT')
    def test_unsafe_pool_and_limit(self):
        for path in ('../Rows.ets', '/Rows.ets', './Rows.ets'):
            pool = deepcopy(self.pool); pool[0]['file_path'] = path
            self.assertIsNone(self.frames(pool))
        pool = deepcopy(self.pool) + [dict(kind='file', file_path=str(i)+'.ets') for i in range(65)]
        self.assertIsNone(self.frames(pool))


class VerticalScopeCapacity(unittest.TestCase):
    """Isolated SQLite metadata tests: no init/learn/context CLI execution."""
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
    def fixture(self, total, matching=1):
        import hashlib, sqlite3
        from pathlib import Path
        from types import SimpleNamespace
        from tools.agent_memory_runtime.query_command_table_scope import IDENTITY
        root=Path(self.tmp.name);db_path=root/'scope.sqlite3'
        project=SimpleNamespace(root=root,db_path=db_path,project_id='scope-unit')
        db=sqlite3.connect(db_path)
        db.executescript('DROP TABLE IF EXISTS projects; DROP TABLE IF EXISTS code_index_state; DROP TABLE IF EXISTS code_files; DROP TABLE IF EXISTS code_symbols;')
        db.execute('CREATE TABLE projects (project_id TEXT, project_path TEXT)')
        db.execute('INSERT INTO projects VALUES (?,?)',(project.project_id,str(root)))
        db.execute('CREATE TABLE code_index_state (project_id TEXT, generation INTEGER, status TEXT)')
        db.execute('INSERT INTO code_index_state VALUES (?,1,?)',(project.project_id,'active'))
        db.execute('CREATE TABLE code_files (id INTEGER, project_id TEXT, file_path TEXT, language TEXT, source_digest TEXT, index_generation INTEGER)')
        columns=list(IDENTITY)
        numeric={'id','start_line','end_line','index_generation'}
        db.execute('CREATE TABLE code_symbols ('+','.join(k+(' INTEGER'if k in numeric else' TEXT')for k in columns)+')')
        pool=[]
        for i in range(total):
            name='InvoiceRows'+str(i);path=('Rows'+str(i)+'.ets')if i<matching else('Neutral'+str(i)+'.ts')
            source=SOURCE.replace('InvoiceRows',name)if i<matching else'export class Neutral'+str(i)+' {}'
            (root/path).write_text(source)
            digest=hashlib.sha256(source.encode()).hexdigest()
            file=dict(id=i+1,project_id=project.project_id,file_path=path,language='ArkTS'if i<matching else'TypeScript',source_digest=digest,index_generation=1)
            db.execute('INSERT INTO code_files VALUES (?,?,?,?,?,?)',tuple(file.values()));pool.append(dict(file,kind='file'))
            if i>=matching:continue
            for method in (False,True):
                symbol='build'if method else name
                row=dict(id=2*i+1+int(method),project_id=project.project_id,file_path=path,symbol=symbol,
                    symbol_key='symbol:'+str(i)+':'+symbol,qualified_name=name+'.build'if method else name,
                    start_line=4 if method else 2,end_line=10 if method else 11,source_digest=digest,index_generation=1,
                    owner_name=name if method else'',owner_kind='component',semantic_adapter='arkts-static@1.2',
                    evidence_class='static',symbol_type='function'if method else'component',signature='build():unknown'if method else'struct '+name)
                db.execute('INSERT INTO code_symbols VALUES ('+','.join('?'for _ in columns)+')',tuple(row[k]for k in columns))
                pool.append(dict(row,kind='symbol'))
        db.commit();db.close()
        return project,pool
    def test_total_64_current_paths_allowed(self):
        project,pool=self.fixture(64)
        frames=vertical_frames(project,pool,'invoice')
        self.assertIsNotNone(frames)
        self.assertEqual(len(frames),1)
        self.assertEqual(len(frames[0]['scope_files']),64)
        self.assertEqual({r['file_path']for r in frames[0]['scope_files']},set(frames[0]['pool_paths']))
    def test_total_65_paths_rejected(self):
        project,pool=self.fixture(65)
        self.assertIsNone(vertical_frames(project,pool,'invoice'))
    def test_matching_13_still_rejected(self):
        project,pool=self.fixture(13,13)
        self.assertIsNone(vertical_frames(project,pool,'invoice'))
    def test_total_64_does_not_supply_missing_typed_root(self):
        project,pool=self.fixture(64,2)
        self.assertEqual(len(vertical_frames(project,pool,'invoice')),2)
        pool=[r for r in pool if not(r['kind']=='symbol'and r['file_path']=='Rows1.ets')]
        self.assertIsNone(vertical_frames(project,pool,'invoice'))
    def test_total_64_missing_nonmatching_file_metadata_rejects(self):
        project,pool=self.fixture(64)
        with connect(project)as db:db.execute("DELETE FROM code_files WHERE file_path='Neutral63.ts'")
        self.assertIsNone(vertical_frames(project,pool,'invoice'))
    def test_total_64_stale_nonmatching_file_rejects(self):
        project,pool=self.fixture(64)
        with connect(project)as db:db.execute("UPDATE code_files SET index_generation=2 WHERE file_path='Neutral63.ts'")
        for row in pool:
            if row['file_path']=='Neutral63.ts':row['index_generation']=2
        self.assertIsNone(vertical_frames(project,pool,'invoice'))
    def test_total_64_source_only_path_is_retained_for_inventory_check(self):
        # Metadata scope cannot certify source-only names. It exposes EVERY path
        # and current digest for the separate complete source inventory contract.
        project,pool=self.fixture(64,2)
        with connect(project)as db:db.execute("DELETE FROM code_symbols WHERE file_path='Rows1.ets'")
        pool=[r for r in pool if not(r['kind']=='symbol'and r['file_path']=='Rows1.ets')]
        frames=vertical_frames(project,pool,'invoice')
        self.assertIsNotNone(frames)
        self.assertIn('Rows1.ets',[r['file_path']for r in frames[0]['scope_files']])
        self.assertEqual(len(frames),1)  # Inventory must reject; scope cannot invent that root.

if __name__ == '__main__': unittest.main()
