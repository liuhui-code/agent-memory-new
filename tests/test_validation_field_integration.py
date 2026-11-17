# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Normal init/learn/facade tests; finite view, not an evaluation rerun."""
from copy import deepcopy
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tests.archive_create_write_test_support import cli,snapshot_database,restore_database
from tools.agent_memory_runtime.storage import resolve_project,connect
from tools.agent_memory_runtime.context_composition import build_context_facade
from tools.agent_memory_runtime.context_compact import compact_context
from tools.agent_memory_runtime.context_record_loop_transaction import restore_whitelist

F=json.loads((Path(__file__).parent/'fixtures/validation_field_source.json').read_text())
Q='Locate the account validation-stop and dispatch source.'
TABLES=('query_misses','project_counters','experience_usage_events','reflection_reuse_events','episodes','semantic_facts','reflections')
TIMES={'created_at','updated_at','last_used_at','last_seen_at','last_applied_at'}

def accounting(project,ignore_times=False):
    with connect(project)as db:
        result={t:[dict(r)for r in db.execute('SELECT * FROM '+t+' ORDER BY rowid')]for t in TABLES}
    if ignore_times:
        return {t:[{k:v for k,v in r.items()if k not in TIMES}for r in rows]for t,rows in result.items()}
    return result


def body_covered(output,file,lo,hi,source):
    wanted='\n'.join(source.splitlines()[lo-1:hi])
    for anchor in output['query_handoff']['code_anchors']:
        if anchor.get('file_path')!=file:continue
        for excerpt in anchor.get('source_excerpts',[]):
            start,end=excerpt.get('start_line',10**9),excerpt.get('end_line',0)
            if start<=lo<=hi<=end:
                lines=excerpt.get('content','').splitlines()
                if '\n'.join(lines[lo-start:hi-start+1])==wanted:return True
    return False


class ValidationFieldIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.temp.cleanup);cls.samples={}
        for world in ('account-owner-and-method','existing-three-mixed','display-name-two-shapes','ordinary-logger-coexistence'):
            folder=Path(cls.temp.name)/world;folder.mkdir();source=folder/'source';source.mkdir()
            for name,text in F['sources'][world].items():
                file=source/name;file.parent.mkdir(parents=True,exist_ok=True);file.write_text(text)
            p=resolve_project(str(source),str(folder/'memory'));cli(p,'init');cli(p,'learn-path','--path','.','--json')
            saved=snapshot_database(p);cls.addClassCleanup(saved.close);cls.samples[world]=(p,saved)
    def pair(self,world,query):
        p,saved=self.samples[world];restore_database(p,saved)
        with patch('tools.agent_memory_runtime.query_validation_field_selection.bind_validation_field_context',side_effect=lambda project,query,data,items,collection=None:data):
            ordinary_raw=build_context_facade(p).execute(query);ordinary=compact_context(ordinary_raw)
        ordinary_counts=accounting(p,ignore_times=True)
        restore_database(p,saved)
        raw=build_context_facade(p).execute(query);before_compact=accounting(p)
        result=compact_context(raw)
        self.assertEqual(accounting(p),before_compact)
        self.assertEqual(compact_context(raw),result)
        self.assertEqual(accounting(p),before_compact)
        self.assertEqual(accounting(p,ignore_times=True),ordinary_counts)
        self.assertEqual(dict(raw),dict(ordinary_raw))
        self.assertEqual(restore_whitelist(result,ordinary),ordinary)
        self.assertEqual(result['query_handoff']['log_anchors'],ordinary['query_handoff']['log_anchors'])
        self.assertEqual(result['query_handoff'].get('path_context'),ordinary['query_handoff'].get('path_context'))
        self.assertLessEqual(result['output_budget']['estimated_tokens'],min(1500,result['output_budget']['target_tokens']))
        return raw,result,ordinary
    def test_complete_two_domain_methods_and_accounting_once(self):
        _,result,_=self.pair('account-owner-and-method',Q)
        self.assertEqual({a['file_path']for a in result['query_handoff']['code_anchors']},{'AccountDraftPanel.ts','MemberDraftPanel.ts'})
        for name in ('AccountDraftPanel.ts','MemberDraftPanel.ts'):
            self.assertTrue(body_covered(result,name,3,9,F['sources']['account-owner-and-method'][name]))
    def test_observation_same_contract_complete_set(self):
        query='A required account field shows an error but the invalid update still submits. Locate the validation-stop and dispatch owner.'
        _,result,_=self.pair('account-owner-and-method',query)
        for name in ('AccountDraftPanel.ts','MemberDraftPanel.ts'):
            self.assertTrue(body_covered(result,name,3,9,F['sources']['account-owner-and-method'][name]))
    def test_original_name_collision_guard_stays_fallback(self):
        _,result,ordinary=self.pair('existing-three-mixed','Locate the display name validation-stop and dispatch source.')
        self.assertEqual(result,ordinary)
    def test_named_path_and_unsupported_requests_exact_fallback(self):
        for query in ('Locate AccountDraftPanel.submitDraft implementation.','Trace the call path from AccountDraftPanel.submitDraft to dispatchDraft.','Locate the account validation-stop and dispatch source. Return the logger.'):
            _,result,ordinary=self.pair('account-owner-and-method',query);self.assertEqual(result,ordinary)
    def test_existing_complete_envelopes_not_falsely_red(self):
        _,result,_=self.pair('display-name-two-shapes','Locate the display name validation-stop and dispatch source.')
        for name in ('BadgeDraftPanel.ts','RosterDraftForm.ts'):
            self.assertTrue(body_covered(result,name,3,9,F['sources']['display-name-two-shapes'][name]))
    def test_logger_or_missing_roots_remains_fallback(self):
        _,result,ordinary=self.pair('ordinary-logger-coexistence','必填显示名为空时提示错误但仍提交更新，请定位校验中止和动作分发源码。')
        self.assertEqual(result,ordinary)
    def test_coverage_helper_accepts_class_envelope(self):
        text='class A {\n  run() {\n    work()\n  }\n}'
        value={'query_handoff':{'code_anchors':[{'file_path':'A.ts','symbol':'A','source_excerpts':[{'start_line':1,'end_line':5,'content':text}]}]}}
        self.assertTrue(body_covered(value,'A.ts',2,4,text))
        value['query_handoff']['code_anchors'][0]['source_excerpts'][0]['content']=text.replace('work()','other()')
        self.assertFalse(body_covered(value,'A.ts',2,4,text))
