# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
from __future__ import annotations
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tools.agent_memory_runtime.complete_dependency_scope import (
    DiscoveryBudget, IncompleteDependencyDiscovery, complete_reverse_paths,
    complete_dispatch_paths,
)
from tools.agent_memory_runtime.code_passages import create_code_passage_schema
from tools.agent_memory_runtime.code_wiki_edges import dependent_file_paths_for_scope
from tools.agent_memory_runtime.code_wiki_indexing import write_wiki_index
from tools.agent_memory_runtime.storage import resolve_project, ensure_initialized, connect
from tools.agent_memory_runtime.transactional_schema import execute_schema


def graph(count: int, relation: str = 'calls') -> sqlite3.Connection:
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.executescript('''CREATE TABLE memory_edges(id INTEGER PRIMARY KEY, project_id TEXT,
    source_type TEXT, source_id INTEGER, relation TEXT, target_type TEXT, target_id INTEGER,
    valid_to TEXT); CREATE TABLE code_symbols(id INTEGER PRIMARY KEY, project_id TEXT,
    file_path TEXT, symbol TEXT); CREATE TABLE code_files(id INTEGER PRIMARY KEY,
    project_id TEXT, file_path TEXT); CREATE TABLE code_log_statements(id INTEGER PRIMARY KEY,
    project_id TEXT, file_path TEXT);''')
    conn.execute("INSERT INTO code_symbols VALUES(1,'p','Leaf.ts','Leaf')")
    conn.executemany("INSERT INTO code_symbols VALUES(?,'p',?,'step')",
                     [(i+2, f'Caller{i+1:04}.ts') for i in range(count)])
    conn.executemany("INSERT INTO memory_edges VALUES(?,'p','code_symbol',?,?,'code_symbol',1,NULL)",
                     [(i+1, i+2, relation) for i in range(count)])
    conn.commit()
    return conn


class CompleteDiscoveryTests(unittest.TestCase):
    def test_original_truncation_remains_observable(self):
        with graph(2001) as conn:
            self.assertEqual(2000, len(dependent_file_paths_for_scope(
                conn, 'p', {'code_symbol': {1}})))

    def test_width_boundaries_complete(self):
        for n in (1999, 2000, 2001):
            with self.subTest(n=n), graph(n) as conn:
                actual = complete_reverse_paths(conn, 'p', {'code_symbol': {1}}, DiscoveryBudget())
                self.assertEqual([f'Caller{i:04}.ts' for i in range(1,n+1)], actual)

    def test_single_row_pages_and_duplicate_entities(self):
        with graph(3) as conn:
            conn.execute("INSERT INTO memory_edges VALUES(90,'p','code_symbol',2,'calls','code_symbol',1,NULL)")
            conn.execute("UPDATE code_symbols SET file_path='Caller0001.ts' WHERE id=3")
            result=complete_reverse_paths(conn,'p',{'code_symbol':{1}},DiscoveryBudget(page_size=1))
            self.assertEqual(['Caller0001.ts','Caller0003.ts'],result)

    def test_seed_chunks_stale_and_other_project(self):
        with graph(0) as conn:
            seeds=set(range(1,402))
            for seed in range(2,402):
                conn.execute("INSERT INTO code_symbols VALUES(?,'p',?,'seed')",(seed,f'S{seed}.ts'))
            for seed in seeds:
                caller=1000+seed
                conn.execute("INSERT INTO code_symbols VALUES(?,'p',?,'caller')",(caller,f'C{seed:04}.ts'))
                conn.execute("INSERT INTO memory_edges VALUES(?,'p','code_symbol',?,'calls','code_symbol',?,NULL)",(seed,caller,seed))
            conn.execute("INSERT INTO memory_edges VALUES(9000,'other','code_symbol',99999,'calls','code_symbol',1,NULL)")
            conn.execute("INSERT INTO memory_edges VALUES(9001,'p','code_symbol',99998,'calls','code_symbol',1,'retired')")
            actual=complete_reverse_paths(conn,'p',{'code_symbol':seeds},DiscoveryBudget(page_size=1))
            self.assertEqual([f'C{i:04}.ts' for i in range(1,402)],actual)

    def test_dispatch_complete(self):
        with tempfile.TemporaryDirectory() as root, graph(2001,'dispatches_via') as conn:
            path=Path(root); (path/'Changed.ts').write_text('class Changed implements Leaf {}')
            result=complete_dispatch_paths(conn,SimpleNamespace(root=path,project_id='p'),
                                           ['Changed.ts'],set(),DiscoveryBudget())
            self.assertEqual(2002,len(result))
            self.assertIn('Caller2001.ts',result)

    def test_budgets_refuse_without_mutation(self):
        options=[{'max_rows':0},{'max_queries':0},{'max_paths':0},
                 {'max_seconds':-1},{'page_size':0}]
        for option in options:
            with self.subTest(option=option), graph(10) as conn:
                before=list(conn.iterdump())
                with self.assertRaises(IncompleteDependencyDiscovery):
                    complete_reverse_paths(conn,'p',{'code_symbol':{1}},DiscoveryBudget(**option))
                self.assertEqual(before,list(conn.iterdump()))

    def test_dispatch_source_budget(self):
        with tempfile.TemporaryDirectory() as root, graph(1) as conn:
            path=Path(root); (path/'C.ts').write_text('class C implements Leaf {}')
            with self.assertRaises(IncompleteDependencyDiscovery):
                complete_dispatch_paths(conn,SimpleNamespace(root=path,project_id='p'),
                                        ['C.ts'],set(),DiscoveryBudget(max_source_bytes=1))

    def test_missing_endpoint_refuses(self):
        with graph(2) as conn:
            conn.execute('DELETE FROM code_symbols WHERE id=3')
            with self.assertRaises(IncompleteDependencyDiscovery):
                complete_reverse_paths(conn,'p',{'code_symbol':{1}},DiscoveryBudget())

    def test_three_hops_unchanged(self):
        with graph(0) as conn:
            for i in range(2,6):
                conn.execute("INSERT INTO code_symbols VALUES(?,'p',?,'step')",(i,f'C{i}.ts'))
                conn.execute("INSERT INTO memory_edges VALUES(?,'p','code_symbol',?,'calls','code_symbol',?,NULL)",(i,i,i-1))
            self.assertEqual(['C2.ts','C3.ts','C4.ts'],complete_reverse_paths(conn,'p',{'code_symbol':{1}},DiscoveryBudget()))

    def test_script_retains_transaction_and_trigger(self):
        conn=sqlite3.connect(':memory:'); conn.row_factory=sqlite3.Row
        conn.execute('CREATE TABLE marker(n INTEGER)');conn.commit()
        conn.execute('INSERT INTO marker VALUES(1)')
        create_code_passage_schema(conn)
        self.assertTrue(conn.in_transaction)
        self.assertEqual(3,conn.execute("SELECT count(*) FROM sqlite_master WHERE type='trigger' AND name LIKE 'code_passage_fts_%'").fetchone()[0])
        conn.rollback()
        self.assertEqual(0,conn.execute('SELECT count(*) FROM marker').fetchone()[0])
        self.assertEqual(0,conn.execute("SELECT count(*) FROM sqlite_master WHERE name='code_passages'").fetchone()[0])

    def test_schema_upgrade_rollback(self):
        conn=sqlite3.connect(':memory:'); conn.row_factory=sqlite3.Row
        conn.executescript("CREATE TABLE code_passages(id INTEGER PRIMARY KEY, old TEXT); "
                           "INSERT INTO code_passages VALUES(1,'keep');")
        before=list(conn.iterdump())
        conn.execute('BEGIN IMMEDIATE')
        create_code_passage_schema(conn)
        self.assertTrue(conn.in_transaction)
        self.assertIn('mechanism_terms',[r['name'] for r in conn.execute('PRAGMA table_info(code_passages)')])
        conn.rollback()
        self.assertEqual(before,list(conn.iterdump()))

    def test_unreadable_changed_source_refuses(self):
        with tempfile.TemporaryDirectory() as root, graph(1) as conn:
            with self.assertRaises(IncompleteDependencyDiscovery):
                complete_dispatch_paths(conn,SimpleNamespace(root=Path(root),project_id='p'),
                                        ['missing.ts'],set(),DiscoveryBudget())

    def test_script_quoted_semicolons(self):
        conn=sqlite3.connect(':memory:')
        execute_schema(conn,"CREATE TABLE x(a TEXT); INSERT INTO x VALUES('a;b');")
        self.assertEqual('a;b',conn.execute('SELECT a FROM x').fetchone()[0])


class IndexRollbackTests(unittest.TestCase):
    def test_writer_failure_preserves_database(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'src';root.mkdir()
            source=root/'Leaf.ts';source.write_text('class Leaf {\n step(): string { return "before"; }\n}\n')
            project=resolve_project(str(root),str(Path(temporary)/'memory'))
            ensure_initialized(project);write_wiki_index(project,[source],True)
            with connect(project) as conn:
                before=list(conn.iterdump())
            source.write_text('class Leaf {\n step(): string { return "after"; }\n}\n')
            for point in ['begin_memory_edge_tracking','rebuild_code_passages',
                          'finish_memory_edge_tracking','activate_index_generation']:
                with self.subTest(point=point), patch(
                    f'tools.agent_memory_runtime.code_wiki_indexing.{point}',
                    side_effect=RuntimeError('injected')):
                    with self.assertRaisesRegex(RuntimeError,'injected'):
                        write_wiki_index(project,[source])
                with connect(project) as conn:
                    self.assertEqual(before,list(conn.iterdump()))

    def test_rollback_after_generation_activation(self):
        from tools.agent_memory_runtime import code_wiki_indexing as indexing
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'src';root.mkdir()
            source=root/'Leaf.ts';source.write_text('class Leaf {}')
            project=resolve_project(str(root),str(Path(temporary)/'memory'))
            ensure_initialized(project);write_wiki_index(project,[source],True)
            with connect(project) as conn: before=list(conn.iterdump())
            source.write_text('class Leaf {\n  step(): number { return 2; }\n}')
            original=indexing.activate_index_generation
            reached=[]
            def fail_after(*args,**kwargs):
                original(*args,**kwargs)
                reached.append(True)
                raise RuntimeError('after activation')
            with patch.object(indexing,'activate_index_generation',side_effect=fail_after):
                with self.assertRaisesRegex(RuntimeError,'after activation'):
                    write_wiki_index(project,[source])
            self.assertEqual([True],reached)
            with connect(project) as conn:self.assertEqual(before,list(conn.iterdump()))

    def test_declared_retired_source_does_not_require_read(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'src';root.mkdir()
            source=root/'Leaf.ts';source.write_text('class Leaf {}')
            project=resolve_project(str(root),str(Path(temporary)/'memory'))
            ensure_initialized(project);write_wiki_index(project,[source],True)
            source.unlink()
            result=write_wiki_index(project,[],retired_relative_files=['Leaf.ts'])
            self.assertEqual(0,result['files_indexed'])
            with connect(project) as conn:
                self.assertEqual(0,conn.execute('SELECT count(*) FROM code_files').fetchone()[0])

    def test_discovery_rejection_before_tracking(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'src';root.mkdir()
            source=root/'Leaf.ts';source.write_text('class Leaf {}')
            project=resolve_project(str(root),str(Path(temporary)/'memory'))
            ensure_initialized(project);write_wiki_index(project,[source],True)
            with connect(project) as conn: before=list(conn.iterdump())
            with patch('tools.agent_memory_runtime.code_wiki_indexing.complete_reverse_paths',
                       side_effect=IncompleteDependencyDiscovery('incomplete')), patch(
                       'tools.agent_memory_runtime.code_wiki_indexing.begin_memory_edge_tracking') as track:
                with self.assertRaises(IncompleteDependencyDiscovery):
                    write_wiki_index(project,[source])
                track.assert_not_called()
            with connect(project) as conn:self.assertEqual(before,list(conn.iterdump()))
