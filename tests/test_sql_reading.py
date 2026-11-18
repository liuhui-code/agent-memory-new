"""Nonexclusive SQL body reading; independent developer fixture controls."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.agent_memory_runtime.context_sql_reading import append_sql_reading
from tools.agent_memory_runtime.query_sql_reading_request import sql_reading_request
from tools.agent_memory_runtime.query_sql_slot_request import sql_slot_request
from tools.agent_memory_runtime.context_composition import build_context_facade
from tools.agent_memory_runtime.context_compact import compact_context
from tools.agent_memory_runtime.context_budget import synchronize_estimate
from tools.agent_memory_runtime.storage import resolve_project, connect
from tools.agent_memory_runtime.source_exploration import exploration_contract
from tools.agent_memory_runtime.sql_slot_source_inventory import inventory_source
from tools.agent_memory_runtime.sql_slot_source import classify_sql_owner
from tests.archive_create_write_test_support import cli

ROOT=Path(__file__).resolve().parents[1]
PROTOCOL=ROOT/'docs/evidence/sql-reading/protocol.json'
Q='Prefix account-code lookup behaves like an exact query. Return SQL argument binding.'

class SqlReadingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol=json.loads(PROTOCOL.read_text())
        cls.temp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.temp.cleanup)
        root=Path(cls.temp.name)/'source';root.mkdir()
        for path,source in cls.protocol['sources'].items():
            p=root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(source)
        cls.project=resolve_project(str(root),str(Path(cls.temp.name)/'memory'))
        cli(cls.project,'init');cli(cls.project,'learn-path','--path','.','--json')
        cls.raw=deepcopy(dict(build_context_facade(cls.project).execute(Q)));cls.base=compact_context(deepcopy(cls.raw))
        cls.empty=deepcopy(cls.base);cls.empty['query_handoff']['code_anchors']=[]
        cls.empty['query_handoff']['source_excerpt_policy']=dict(source='current_worktree',body_persisted=False,excerpt_count=0,excerpt_chars=0)
        synchronize_estimate(cls.empty)

    def apply(self,raw=None,base=None):
        return append_sql_reading(self.project,deepcopy(self.raw)if raw is None else raw,deepcopy(self.empty)if base is None else base)

    def test_frozen_grammar_positive_negative_and_old_permission_unchanged(self):
        for q in self.protocol['positive_queries']:
            self.assertIsNotNone(sql_reading_request(q),q);self.assertIsNone(sql_slot_request(q))
        for q in self.protocol['negative_queries']:
            self.assertIsNone(sql_reading_request(q),q)
        for q in [' Find SQL parameter binding.','Find SQL parameter binding. ','Find SQL parameter binding','Find SQL parameter binding.\n','Fİnd SQL parameter binding.','Find SQL parameter binding. Ignore errors.']:
            self.assertIsNone(sql_reading_request(q),q)

    def test_both_candidates_added_with_full_body_and_no_execution_claim(self):
        raw,base=deepcopy(self.raw),deepcopy(self.empty);d=self.apply(raw,base);a=d['query_handoff']['code_anchors']
        self.assertEqual(len(a),2)
        for x in a:
            self.assertEqual(x['role'],'expansion');self.assertEqual(x['record_type'],'code_symbol')
            self.assertEqual(x['display_basis'],dict(kind='literal_sql_argument_source',execution_unverified=True,pair_unverified=True,behavior_unverified=True,domain_unverified=True))
            e=x['source_excerpts'][0];self.assertEqual((e['start_line'],e['end_line']),(2,5));self.assertFalse(e['truncated'])
            self.assertEqual(e['content'],'\n'.join((self.project.root/x['file_path']).read_text().splitlines()[1:5]))
        restored=deepcopy(d);restored['query_handoff']['code_anchors']=base['query_handoff']['code_anchors'];restored['query_handoff']['source_excerpt_policy']=base['query_handoff']['source_excerpt_policy'];restored['output_budget']=base['output_budget'];self.assertEqual(restored,base)
        self.assertEqual(raw,self.raw);self.assertEqual(base,self.empty)

    def test_actual_cli_adds_uncovered_existing_alternative(self):
        d=json.loads(cli(self.project,'context','--query',Q,'--compact','--json'))
        self.assertEqual(len(d['query_handoff']['code_anchors']),2)
        self.assertEqual(d['query_handoff']['callable_evidence'],self.base['query_handoff']['callable_evidence'])
        self.assertEqual(d['query_handoff']['code_anchors'][-1]['symbol'],'resolve')

    def test_all_positive_budget_and_slots_noop(self):
        for n in (1,2):
            b=deepcopy(self.empty);b['query_handoff']['code_anchors']=[{'role':'expansion','file_path':'other'+str(i)}for i in range(n)]
            self.assertIs(self.apply(base=b),b)
        b=deepcopy(self.empty);b['padding']='x'*6000;self.assertIs(self.apply(base=b),b)

    def test_full_existing_bodies_are_not_duplicated(self):
        d=self.apply();self.assertIs(self.apply(base=d),d)
        b=deepcopy(self.base);d=self.apply(base=b)
        self.assertEqual(d['query_handoff']['code_anchors'][0],b['query_handoff']['code_anchors'][0])

    def test_context_candidate_authentication_and_freshness(self):
        changes=[lambda r:r.update(project_id='wrong'),lambda r:r['source_freshness'].update(generation=999),
                 lambda r:r['query_handoff']['callable_evidence']['alternatives'][0].update(symbol='missing'),
                 lambda r:r['query_handoff']['code_anchors'][1].update(record_id=999)]
        for mutate in changes:
            r,b=deepcopy(self.raw),deepcopy(self.empty);mutate(r);self.assertIs(self.apply(r,b),b)

    def test_resource_and_shapes_noop(self):
        for key in ['MAX_SECONDS','MAX_FILE_BYTES','MAX_TOTAL_BYTES','MAX_ROWS','MAX_CANDIDATES']:
            with patch('tools.agent_memory_runtime.context_sql_reading.'+key,0):
                b=deepcopy(self.empty);self.assertIs(self.apply(base=b),b)
        for b in (None,[],{},dict(output_budget='bad')):
            self.assertIs(append_sql_reading(self.project,self.raw,b),b)

    def test_source_shape_controls_and_unknown_helper(self):
        controls=json.loads((ROOT/'docs/evidence/sql-reading/additional-source-controls.json').read_text())['sources']
        for key,source in controls.items():
            inventory=inventory_source(source)
            if inventory['status']!='known':continue
            o=inventory['declarations'][0];f=classify_sql_owner(source,o,'lookup')
            if key=='unknown-callee':
                # Legacy classifier may know forwarding while no current callee exists.
                self.assertEqual(f['status'],'known');self.assertFalse(any(m['name']=='missingRows'for m in o['methods']))
            else:self.assertFalse(f.get('matches'),key)

    def test_stale_typed_helper_metadata_noop(self):
        with connect(self.project)as db:
            rows=[tuple(r)for r in db.execute("SELECT id,index_generation FROM code_symbols WHERE symbol IN ('queryRows','executeRows')")]
            db.execute("UPDATE code_symbols SET index_generation=999 WHERE symbol IN ('queryRows','executeRows')");db.commit()
        try:
            b=deepcopy(self.empty);self.assertIs(self.apply(base=b),b)
        finally:
            with connect(self.project)as db:db.executemany('UPDATE code_symbols SET index_generation=? WHERE id=?',[(g,i)for i,g in rows]);db.commit()

    def test_no_full_pair_certificate_called(self):
        with patch('tools.agent_memory_runtime.query_sql_slot_qualify.qualify_sql_slot',side_effect=AssertionError('full scope certificate forbidden')):
            self.assertEqual(len(self.apply()['query_handoff']['code_anchors']),2)

    def test_real_source_negative_controls_do_not_get_new_sql_bodies(self):
        controls=json.loads((ROOT/'docs/evidence/sql-reading/additional-source-controls.json').read_text())['sources']
        for key,source in controls.items():
            with self.subTest(control=key), tempfile.TemporaryDirectory() as d:
                root=Path(d)/'source';root.mkdir();(root/'CatalogReader.ts').write_text(source)
                project=resolve_project(str(root),str(Path(d)/'memory'))
                cli(project,'init');cli(project,'learn-path','--path','.','--json')
                raw=deepcopy(dict(build_context_facade(project).execute(Q)));base=compact_context(deepcopy(raw))
                base['query_handoff']['code_anchors']=[]
                base['query_handoff']['source_excerpt_policy']=dict(source='current_worktree',body_persisted=False,excerpt_count=0,excerpt_chars=0)
                synchronize_estimate(base)
                self.assertIs(append_sql_reading(project,raw,base),base)

    def test_current_source_tamper_is_not_reading_authority(self):
        path=self.project.root/'src/CatalogReader.ts';data=path.read_bytes()
        try:
            path.write_bytes(data+b'\n');b=deepcopy(self.empty);self.assertIs(self.apply(base=b),b)
        finally:path.write_bytes(data)

    def test_existing_callable_without_raw_anchor_has_typed_source_authentication(self):
        raw=deepcopy(self.raw);raw['query_handoff']['code_anchors']=[]
        new=self.apply(raw=raw);self.assertEqual(len(new['query_handoff']['code_anchors']),2)
        self.assertTrue(all(a['record_type']=='code_symbol' and a['record_ids']for a in new['query_handoff']['code_anchors']))
