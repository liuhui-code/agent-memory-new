import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from tools.agent_memory_runtime.receiver_empty_transaction import EmptyReceiverSession, defer_accounting
from tools.agent_memory_runtime.storage import resolve_project
from tools.agent_memory_runtime.query_results import limited_context

Q='请定位遍历记录时累加状态总数的聚合源码。'
SOURCE='''class Inventory {
  total: number = 0
  rows: Item[] = []
  refresh() {
    this.total = 0
    this.rows.forEach((row: Item) => {
      this.total += row.quantity
    })
  }
}
'''
R=Path(__file__).resolve().parents[1]
class ReceiverEmptyTransactionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)/'source';self.root.mkdir();self.home=Path(self.temp.name)/'memory'
    def tearDown(self):self.temp.cleanup()
    def run_cli(self,*args):
        p=subprocess.run([sys.executable,'-B',str(R/'tools/agent_memory.py'),*args,'--project',str(self.root),'--memory-home',str(self.home)],capture_output=True,text=True)
        self.assertEqual(0,p.returncode,p.stderr);return json.loads(p.stdout)if '--json'in args else p.stdout
    def init(self,n=1):
        for i in range(n):(self.root/f'Inventory{i}.ts').write_text(SOURCE.replace('Inventory',f'Inventory{i}'))
        self.run_cli('init');self.run_cli('learn-path','--path',str(self.root))
    def misses(self):
        with sqlite3.connect(next(self.home.glob('projects/*/memory.db')))as c:return c.execute('select normalized_query from query_misses').fetchall()
    def test_public_raw_compact_and_direct_accounting(self):
        self.init()
        for flags in ((),('--compact',),('--compact','--compact-token-budget','2000','--preserve-selected-source-anchors')):
            x=self.run_cli('context','--query',Q,'--json',*flags)
            anchors=x['query_handoff']['code_anchors'];self.assertEqual(1,len(anchors));self.assertEqual((4,9),(anchors[0]['source_excerpts'][0]['start_line'],anchors[0]['source_excerpts'][0]['end_line']))
            self.assertIn('source_snapshot',anchors[0]);self.assertFalse(self.misses())
        p=resolve_project(str(self.root),str(self.home));x=limited_context(p,Q)
        self.assertEqual([],x['query_handoff']['code_anchors']);self.assertEqual(1,len(self.misses()))
    def test_nonempty_does_not_supplement(self):
        self.init(2);x=self.run_cli('context','--query','Locate Inventory0.refresh source.','--json','--compact')
        self.assertTrue(x['query_handoff']['code_anchors']);self.assertTrue(all('source_snapshot'not in a for a in x['query_handoff']['code_anchors']))
    def test_two_all_and_three_fallback(self):
        self.init(2);x=self.run_cli('context','--query',Q,'--json','--compact');self.assertEqual(2,len(x['query_handoff']['code_anchors']));self.assertFalse(self.misses())
        (self.root/'Inventory2.ts').write_text(SOURCE.replace('Inventory','Inventory2'));self.run_cli('learn-path','--path',str(self.root));x=self.run_cli('context','--query',Q,'--json','--compact');self.assertEqual([],x['query_handoff']['code_anchors']);self.assertEqual(1,len(self.misses()))
    def test_stale_and_over_limit_fallback(self):
        self.init();(self.root/'Inventory0.ts').write_text(SOURCE+'\n// changed')
        x=self.run_cli('context','--query',Q,'--json','--compact');self.assertEqual([],x['query_handoff']['code_anchors'])
        for i in range(12):(self.root/f'Empty{i}.ts').write_text(f'class Empty{i} {{}}')
        self.run_cli('learn-path','--path',str(self.root));x=self.run_cli('context','--query',Q,'--json','--compact');self.assertEqual([],x['query_handoff']['code_anchors'])
    def test_exception_commits_baseline_once(self):
        p=object();base={'query':Q,'source_freshness':{'status':'empty'},'query_handoff':{'code_anchors':[],'callable_evidence':{'primary':None,'alternatives':[]}}}
        with patch('tools.agent_memory_runtime.query_results.record_context_use')as use,patch('tools.agent_memory_runtime.query_results.record_query_miss_if_empty')as miss:
            with self.assertRaises(ValueError):
                with EmptyReceiverSession(p,Q):
                    self.assertTrue(defer_accounting(p,Q,base));raise ValueError('render failed')
            use.assert_called_once_with(p,base);miss.assert_called_once_with(p,'context',Q,base)
            self.assertFalse(defer_accounting(p,Q,base))

    def test_accounting_error_is_not_retried(self):
        p=object();base={'query':Q,'source_freshness':{'status':'empty'},'query_handoff':{'code_anchors':[],'callable_evidence':{'primary':None,'alternatives':[]}}}
        with patch('tools.agent_memory_runtime.query_results.record_context_use') as use, patch('tools.agent_memory_runtime.query_results.record_query_miss_if_empty',side_effect=RuntimeError('db failure')) as miss:
            with self.assertRaises(RuntimeError):
                with EmptyReceiverSession(p,Q) as session:
                    defer_accounting(p,Q,base);session.commit(base)
            self.assertEqual(1,use.call_count);self.assertEqual(1,miss.call_count)
    def test_final_auth_and_budget_fallback_account_baseline(self):
        p=object();base={'query':Q,'source_freshness':{'status':'empty'},'query_handoff':{'code_anchors':[],'callable_evidence':{'primary':None,'alternatives':[]}}}
        output={'query_handoff':{'code_anchors':[],'callable_evidence':{'primary':None,'alternatives':[]}},'output_budget':{'target_tokens':1500}}
        qualified=([{'file_path':'x'}],[{'id':1}])
        for auth in ([qualified,None],[qualified,qualified]):
            with self.subTest(auth=auth),patch('tools.agent_memory_runtime.receiver_empty_transaction.inventory',return_value=('state',)),patch('tools.agent_memory_runtime.receiver_empty_transaction.authenticate',side_effect=auth),patch('tools.agent_memory_runtime.context_record_loop_transaction.apply_record_loop_transaction',return_value=output),patch('tools.agent_memory_runtime.query_results.record_context_use') as use,patch('tools.agent_memory_runtime.query_results.record_query_miss_if_empty') as miss:
                with EmptyReceiverSession(p,Q) as session:
                    defer_accounting(p,Q,base);self.assertIs(output,session.finalize(output))
                use.assert_called_once_with(p,base);miss.assert_called_once_with(p,'context',Q,base)

    def test_existing_callable_alternative_never_taken_over(self):
        from tools.agent_memory_runtime.receiver_empty_transaction import empty_eligible
        base={'query':Q,'source_freshness':{'status':'empty'},'query_handoff':{'code_anchors':[],'callable_evidence':{'primary':None,'alternatives':[{'symbol':'other'}]}}}
        self.assertFalse(empty_eligible(base))
    def test_raw_logs_and_facts_are_preserved(self):
        from copy import deepcopy
        self.init();p=resolve_project(str(self.root),str(self.home));base=limited_context(p,Q)
        logs=[dict(file_path='Other.ts',line=i+1,message='context '+str(i),source='code_log')for i in range(5)]
        base['query_handoff']['log_anchors']=logs
        base['semantic_facts']=[{'id':999,'fact':'existing contextual evidence'}]
        saved=deepcopy(base)
        with EmptyReceiverSession(p,Q) as session:
            self.assertTrue(defer_accounting(p,Q,base));result=session.finalize(base)
        self.assertTrue(result['query_handoff']['code_anchors'])
        self.assertEqual(saved['query_handoff']['log_anchors'],result['query_handoff']['log_anchors'])
        self.assertEqual(saved['semantic_facts'],result['semantic_facts'])
        self.assertEqual(5,result['sufficiency']['coverage']['log_anchor_count'])
