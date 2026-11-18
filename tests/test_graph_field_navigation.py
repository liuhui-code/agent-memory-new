"""Development-only graph navigation qualification; no retrieval score changes."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from tools.agent_memory_runtime.context_graph_field_navigation import append_graph_field_navigation, _import_matches
from tools.agent_memory_runtime.context_composition import build_context_facade
from tools.agent_memory_runtime.context_compact import compact_context
from tools.agent_memory_runtime.context_budget import synchronize_estimate
from tools.agent_memory_runtime.storage import resolve_project, connect
from tools.agent_memory_runtime.source_exploration import exploration_contract
from tests.archive_create_write_test_support import cli

ROOT=Path(__file__).resolve().parents[1]
Q='必填显示名为空时提示错误但仍提交更新，请定位校验中止和动作分发源码。'

class GraphFieldNavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.temp.cleanup)
        root=Path(cls.temp.name)/'source';root.mkdir()
        sources=json.loads((ROOT/'docs/evidence/validation-competition/protocol.json').read_text())['sources']
        for name in ['src/pages/ProfileEditor.ets','src/services/ProfileGateway.ets']:
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(sources[name])
        (root/'src/pages/AlternateEditor.ets').write_text(sources['src/pages/ProfileEditor.ets'].replace('ProfileEditor','AlternateEditor'))
        cls.project=resolve_project(str(root),str(Path(cls.temp.name)/'memory'))
        cli(cls.project,'init');cli(cls.project,'learn-path','--path','.','--json')
        cls.raw=deepcopy(dict(build_context_facade(cls.project).execute(Q)))
        cls.base=compact_context(deepcopy(cls.raw),token_budget=2000,preserve_selected_source_anchors=True)
        cls.empty=deepcopy(cls.base);cls.empty['query_handoff']['code_anchors']=[];cls.empty['query_handoff']['source_exploration']=exploration_contract();synchronize_estimate(cls.empty)

    def apply(self,raw=None,base=None,enabled=True):
        return append_graph_field_navigation(self.project,deepcopy(self.raw) if raw is None else raw,deepcopy(self.empty) if base is None else base,enabled=enabled)

    def test_all_positive_navigation_is_additive_and_typed(self):
        raw,base=deepcopy(self.raw),deepcopy(self.empty);new=self.apply(raw,base)
        added=new['query_handoff']['code_anchors'];self.assertEqual(len(added),2)
        self.assertEqual({a['symbol'] for a in added},{'saveProfile'})
        for a in added:
            self.assertEqual(a['role'],'expansion');self.assertEqual(a['record_type'],'code_symbol')
            self.assertEqual(a['read_window'],{'start_line':6,'end_line':12});self.assertNotIn('source_excerpts',a)
            self.assertTrue(a['display_basis']['action_unverified']);self.assertTrue(a['display_basis']['domain_unverified'])
            self.assertIn(a['display_basis']['edge_id'],[e['id']for e in raw['edge_matches']])
        restored=deepcopy(new);restored['query_handoff']['code_anchors']=base['query_handoff']['code_anchors'];restored['output_budget']=base['output_budget'];self.assertEqual(restored,base)
        self.assertEqual(base,self.empty);self.assertEqual(raw,self.raw)

    def test_public_cli_adds_only_missing_second_source(self):
        d=json.loads(cli(self.project,'context','--query',Q,'--compact','--compact-token-budget','2000','--preserve-selected-source-anchors','--json'))
        self.assertEqual(len(d['query_handoff']['code_anchors']),2)
        new=d['query_handoff']['code_anchors'][-1];self.assertEqual(new['role'],'expansion')
        self.assertEqual(new['read_window'],dict(start_line=6,end_line=12))

    def test_explicit_mode_and_budget_gate(self):
        for enabled in (False,None,1):
            base=deepcopy(self.empty);self.assertIs(self.apply(base=base,enabled=enabled),base)
        base=deepcopy(self.empty);base['output_budget']['target_tokens']=1500;self.assertIs(self.apply(base=base),base)

    def test_all_positive_overflow_and_slots_are_noop(self):
        for count in (1,2):
            base=deepcopy(self.empty);base['query_handoff']['code_anchors']=[{'file_path':'other'+str(i),'role':'expansion'}for i in range(count)]
            self.assertIs(self.apply(base=base),base)
        base=deepcopy(self.empty);base['padding']='x'*8000;self.assertIs(self.apply(base=base),base)

    def test_unknown_query_and_wrong_field_do_not_authorize(self):
        for query in ['Find displayName in logs.', '必填客户编号为空时提示错误但仍提交更新，请定位校验中止和动作分发源码。']:
            raw,base=deepcopy(self.raw),deepcopy(self.empty);raw['query']=base['query']=query
            self.assertIs(self.apply(raw,base),base)

    def test_identity_generation_edge_tamper_fail_closed(self):
        for mutate in [lambda r:r.update(project_id='foreign'),lambda r:r['source_freshness'].update(generation=999),
                       lambda r:r['edge_matches'][0].update(source_id=999),lambda r:r['edge_matches'][0].update(valid_to='expired'),
                       lambda r:r['edge_matches'].append(deepcopy(r['edge_matches'][0]))]:
            raw,base=deepcopy(self.raw),deepcopy(self.empty);mutate(raw);self.assertIs(self.apply(raw,base),base)

    def test_database_stale_edge_and_method_metadata_rejected(self):
        mutations=[('memory_edges','valid_to',"'expired'"),('code_symbols','index_generation','999')]
        for table,column,value in mutations:
            with connect(self.project)as db:
                rows=[tuple(r)for r in db.execute(f'SELECT id,{column} FROM {table}')]
                db.execute(f'UPDATE {table} SET {column}={value}');db.commit()
            try:
                base=deepcopy(self.empty);self.assertIs(self.apply(base=base),base)
            finally:
                with connect(self.project)as db:
                    db.executemany(f'UPDATE {table} SET {column}=? WHERE id=?',[(v,i)for i,v in rows]);db.commit()

    def test_source_tamper_and_ambiguous_import_noop(self):
        source=self.project.root/'src/pages/ProfileEditor.ets';old=source.read_bytes()
        try:
            source.write_bytes(old+b'\n');base=deepcopy(self.empty);self.assertIs(self.apply(base=base),base)
        finally:source.write_bytes(old)
        twin=self.project.root/'src/services/ProfileGateway.ts';twin.write_text('export class ProfileGateway {}')
        try:
            base=deepcopy(self.empty);self.assertIs(self.apply(base=base),base)
        finally:twin.unlink()

    def test_resources_and_complete_grammar_required(self):
        for key in ['MAX_SECONDS','MAX_FILE_BYTES','MAX_TOTAL_BYTES','MAX_ROWS_PER_FILE','MAX_EDGES']:
            with patch('tools.agent_memory_runtime.context_graph_field_navigation.'+key,0):
                base=deepcopy(self.empty);self.assertIs(self.apply(base=base),base)
        with patch('tools.agent_memory_runtime.context_graph_field_navigation.guarded_calls',return_value=None):
            base=deepcopy(self.empty);self.assertIs(self.apply(base=base),base)

    def test_import_identity_uses_tokens_not_strings(self):
        source=self.project.root/'src/pages/ProfileEditor.ets';target=self.project.root/'src/services/ProfileGateway.ets'
        self.assertFalse(_import_matches(source,target,self.project.root,"const text = \"from '../services/ProfileGateway'\""))

    def test_unknown_payload_and_owner_type_are_noop(self):
        for payload in (None,[],"bad"):
            self.assertIs(append_graph_field_navigation(self.project,self.raw,payload,enabled=True),payload)
        for value in ('x',[1],None):
            payload=deepcopy(self.empty);payload['output_budget']=value
            self.assertIs(self.apply(base=payload),payload)
        with connect(self.project) as db:
            rows=[tuple(r)for r in db.execute("SELECT id,symbol_type FROM code_symbols WHERE owner_name IS NULL OR owner_name='' ")]
            db.execute("UPDATE code_symbols SET symbol_type='class' WHERE symbol_type='component'");db.commit()
        try:
            base=deepcopy(self.empty);self.assertIs(self.apply(base=base),base)
        finally:
            with connect(self.project)as db:
                db.executemany('UPDATE code_symbols SET symbol_type=? WHERE id=?',[(v,i)for i,v in rows]);db.commit()

    def test_existing_path_is_navigation_not_method_coverage(self):
        base=deepcopy(self.empty)
        base['query_handoff']['code_anchors']=[{'file_path':'src/pages/ProfileEditor.ets','symbol':'build','role':'primary','read_window':{'start_line':13,'end_line':13}}]
        new=self.apply(base=base)
        self.assertEqual(new['query_handoff']['code_anchors'][0],base['query_handoff']['code_anchors'][0])
        self.assertEqual([a['file_path']for a in new['query_handoff']['code_anchors']],['src/pages/ProfileEditor.ets','src/pages/AlternateEditor.ets'])
