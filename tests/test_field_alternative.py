# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
from copy import deepcopy
from unittest.mock import patch
import json
from pathlib import Path
import tempfile
import unittest
from tools.agent_memory_runtime.context_field_alternative import append_field_alternatives, field_read_request, guarded_calls
from tools.agent_memory_runtime.query_validation_field_request import validation_field_request
from tools.agent_memory_runtime.context_composition import build_context_facade
from tools.agent_memory_runtime.context_compact import compact_context
from tools.agent_memory_runtime.storage import resolve_project, connect
from tests.archive_create_write_test_support import cli

Q='请定位显示名为空时提示错误并中止个人资料更新的校验和分发源码。'
ROOT=Path(__file__).resolve().parents[1]

class FieldAlternativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.temp.cleanup)
        source=Path(cls.temp.name)/'source';source.mkdir()
        protocol=json.loads((ROOT/'docs/evidence/validation-competition/protocol.json').read_text())
        for path,text in protocol['sources'].items():
            p=source/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
        cls.project=resolve_project(str(source),str(Path(cls.temp.name)/'memory'))
        cli(cls.project,'init');cli(cls.project,'learn-path','--path','.','--json')
        cls.raw=deepcopy(dict(build_context_facade(cls.project).execute(Q)))
        cls.base=compact_context(deepcopy(cls.raw))
    def test_public_missing_body_added_without_old_field_changes(self):
        raw,base=deepcopy(self.raw),deepcopy(self.base)
        result=append_field_alternatives(self.project,raw,base)
        old=base['query_handoff']['code_anchors'];new=result['query_handoff']['code_anchors']
        self.assertEqual(len(new),len(old)+1)
        anchor=new[-1];self.assertEqual((anchor['symbol'],anchor['read_window']),('saveProfile',dict(start_line=6,end_line=12)))
        self.assertEqual(anchor['display_basis']['unverified_action'],'个人资料更新')
        self.assertTrue(anchor['display_basis']['domain_unverified'])
        expected='\n'.join((Path(self.project.root)/anchor['file_path']).read_text().splitlines()[5:12])
        self.assertEqual(anchor['source_excerpts'][0]['content'],expected)
        restored=deepcopy(result);restored['query_handoff']['code_anchors']=deepcopy(old)
        restored['query_handoff']['source_excerpt_policy']=deepcopy(base['query_handoff']['source_excerpt_policy'])
        restored['output_budget']=deepcopy(base['output_budget']);self.assertEqual(restored,base)
        self.assertEqual(raw,self.raw);self.assertEqual(base,self.base)
        self.assertLessEqual(result['output_budget']['estimated_tokens'],1500)
        self.assertIs(append_field_alternatives(self.project,raw,result),result)
    def test_actual_cli_after_sanitized_freshness(self):
        result=json.loads(cli(self.project,'context','--query',Q,'--compact','--json'))
        additions=[a for a in result['query_handoff']['code_anchors'] if a.get('display_basis')]
        self.assertEqual(len(additions),1)
        self.assertEqual(additions[0]['source_excerpts'][0]['end_line'],12)
        self.assertEqual(result['query_handoff']['callable_evidence']['primary']['symbol'],'error')
    def test_guarded_call_not_dispatch_name_or_runtime_claim(self):
        from tools.agent_memory_runtime.validation_field_source import parse_validation_field_file
        source=(Path(self.project.root)/'src/pages/ProfileEditor.ets').read_text()
        for name in ['updateProfile','audit','preview','noop','dispatchProfile']:
            changed=source.replace('updateProfile',name)
            self.assertEqual(len(guarded_calls(changed)),1)
            self.assertEqual(guarded_calls(changed)[0]['call_argument'],'scalar')
            if 'dispatch' not in name.lower():self.assertIsNone(parse_validation_field_file(changed))
        for changed in [source.replace('      return','      this.gateway.updateProfile(this.displayName)'),
                        source.replace('this.gateway.updateProfile(this.displayName)','this.gateway.updateProfile(this.missing)'),
                        source.replace('this.gateway.updateProfile','missing.updateProfile')]:
            self.assertIsNone(guarded_calls(changed))
    def test_resource_and_graph_or_window_fail_closed(self):
        for key in ['MAX_FILE_BYTES','MAX_TOTAL_BYTES','MAX_SECONDS']:
            with patch('tools.agent_memory_runtime.context_field_alternative.'+key,0):
                self.assertIs(append_field_alternatives(self.project,self.raw,self.base),self.base)
        raw=deepcopy(self.raw)
        next(a for a in raw['query_handoff']['code_anchors'] if a.get('symbol')=='saveProfile')['graph_neighbor']=True
        self.assertIs(append_field_alternatives(self.project,raw,self.base),self.base)
        base=deepcopy(self.base);base['query_handoff']['callable_evidence']['alternatives'][-1]['source_range']['selection_reason']='semantic_mechanism_window'
        self.assertIs(append_field_alternatives(self.project,self.raw,base),base)
    def test_two_matching_bodies_all_fit_or_none(self):
        from tests.command_table_test_support import prepare
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        sources=json.loads((ROOT/'tests/fixtures/validation_field_source.json').read_text())['sources']['display-name-two-shapes']
        # Use scalar arguments in both independent component sources; no public efficacy claim.
        sources={'One.ts':sources['BadgeDraftPanel.ts'], 'Two.ts':sources['BadgeDraftPanel.ts'].replace('BadgeDraftPanel','OtherDraftPanel').replace('submitBadge','submitOther')}
        p=prepare(t.name,sources=sources)
        with connect(p)as db:
            rows=[dict(r)for r in db.execute("SELECT * FROM code_symbols WHERE symbol IN ('submitBadge','submitOther')")]
        alts=[dict(file_path=r['file_path'],symbol=r['symbol'],owner_name=r['owner_name'],owner_kind=r['owner_kind'],source_range=dict(start_line=r['start_line'],end_line=r['end_line'],selection_reason='callable_symbol_range'))for r in rows]
        rawanchors=[dict(source='wiki',record_type='code_symbol',record_id=r['id'],symbol_type=r['symbol_type'],symbol=r['symbol'],file_path=r['file_path'],start_line=r['start_line'],end_line=r['end_line'],graph_neighbor=False,graph_relation=None)for r in rows]
        raw=dict(query=Q,project_id=p.project_id,project_path=str(p.root),source_freshness=dict(status='current',generation=rows[0]['index_generation']),query_handoff=dict(code_anchors=rawanchors,callable_evidence=dict(alternatives=alts)))
        base=deepcopy(raw);base['query_handoff']['code_anchors']=[];base['query_handoff']['source_excerpt_policy']=dict(excerpt_count=0,excerpt_chars=0);base['output_budget']=dict(estimated_tokens=1,target_tokens=3000,truncated=False)
        both=append_field_alternatives(p,raw,base)
        self.assertEqual(len(both['query_handoff']['code_anchors']),2)
        base['output_budget']['target_tokens']=both['output_budget']['estimated_tokens']-1
        self.assertIs(append_field_alternatives(p,raw,base),base)
    def test_budget_failure_is_atomic_noop(self):
        base=deepcopy(self.base);base['output_budget']['target_tokens']=base['output_budget']['estimated_tokens']
        self.assertIs(append_field_alternatives(self.project,self.raw,base),base)
    def test_raw_root_required_and_identity_conflict(self):
        for change in ['missing','wrong_id','wrong_kind']:
            raw=deepcopy(self.raw);anchors=raw['query_handoff']['code_anchors'];a=next(x for x in anchors if x.get('symbol')=='saveProfile')
            if change=='missing':anchors.remove(a)
            elif change=='wrong_id':a['record_id']=-1
            else:a['symbol_type']='state'
            self.assertIs(append_field_alternatives(self.project,raw,self.base),self.base)
    def test_stale_source_exact_noop(self):
        p=Path(self.project.root)/'src/pages/ProfileEditor.ets';old=p.read_bytes()
        try:
            p.write_bytes(old+b'\n')
            self.assertIs(append_field_alternatives(self.project,self.raw,self.base),self.base)
        finally:p.write_bytes(old)
    def test_different_project_or_generation_noop(self):
        for field,value in [('project_id','wrong'),('source_freshness',dict(status='current',generation=-1))]:
            base=deepcopy(self.base);base[field]=value
            self.assertIs(append_field_alternatives(self.project,self.raw,base),base)
    def test_alternative_identity_conflict_and_duplicate_noop(self):
        for mode in ['name','duplicate']:
            base=deepcopy(self.base);alts=base['query_handoff']['callable_evidence']['alternatives']
            if mode=='name':alts[0]['owner_name']='Elsewhere'
            else:alts.append(deepcopy(alts[0]))
            self.assertIs(append_field_alternatives(self.project,self.raw,base),base)
    def test_weak_permission_does_not_expand_old_view_permission(self):
        self.assertIsNone(validation_field_request(Q))
        self.assertEqual(field_read_request(Q)['field_parts'],('display','name'))
        self.assertEqual(field_read_request(Q.replace('显示名','客户编号'))['field_parts'],('customer','code'))
        self.assertEqual(field_read_request(Q.replace('个人资料更新','账单提交'))['unverified_action'],'账单提交')
        for q in [Q.replace('中止','不中止'),Q.replace('个人资料更新','比较个人资料更新'),Q.replace('显示名','显示名或客户编号'),Q+'返回日志。',Q.replace('个人资料更新','仅个人资料更新'),'Locate the account validation-stop and dispatch source.','Find StatusSink.error']:
            self.assertIsNone(field_read_request(q),q)

if __name__=='__main__':unittest.main()
