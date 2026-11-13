# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import copy
import json
import tempfile
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase

ROOT=Path(__file__).resolve().parents[1]
PROTOCOL=json.loads((ROOT/'docs/evidence/causal-log-followup/protocol.json').read_text())

def subset(a,b):
    return all(k in b and type(v) is type(b[k]) and v==b[k] for k,v in a.items())

class LosslessRangeBudgetTests(AgentMemoryTestBase):
    def test_public_exact_log_budget_has_no_duplicate_range_subsets(self):
        for mode in ('flat','nested','single','three','detailed'):
            with tempfile.TemporaryDirectory() as d:
                root=Path(d);sources=dict(PROTOCOL['sources']);query=PROTOCOL['query']
                if mode=='single':sources.pop('StartupCoordinator.ets')
                if mode=='three':sources['RecoveryCoordinator.ets']=sources['StartupCoordinator.ets'].replace('StartupCoordinator','RecoveryCoordinator').replace('onCreate','onResume')
                if mode=='detailed':
                    before='checkpoint refresh denied expired token'
                    sources={name:source.replace(before,PROTOCOL['pressure_log']) for name,source in sources.items()}
                    query=query.replace(before,PROTOCOL['pressure_log'])
                for name,source in sources.items():
                    if mode=='nested':
                        name=PROTOCOL['layout_control']['mapping'][name]
                        source=source.replace("from './AuditService'","from '../services/AuditService'")
                    file=root/name;file.parent.mkdir(parents=True,exist_ok=True);file.write_text(source)
                self.run_memory(root,'init');self.run_memory(root,'learn-path','--path','.')
                raw=json.loads(self.run_memory(root,'context','--query',query,'--json').stdout)
                compact=json.loads(self.run_memory(root,'context','--query',query,'--compact','--json').stdout)
                h=compact['query_handoff'];paths=h['path_context']['path_candidates']
                raw_ids={p['path_id'] for p in raw['query_handoff']['path_context']['path_candidates']}
                with self.subTest(mode=mode):
                    self.assertLessEqual(compact['output_budget']['estimated_tokens'],1500)
                    self.assertTrue(paths)
                    self.assertTrue({p['path_id'] for p in paths} <= raw_ids)
                    if mode in ('flat','nested'):self.assertEqual(2,len(paths))
                    if mode=='single':self.assertEqual(1,len(paths))
                    for anchor in h['code_anchors']:
                        ranges=anchor.get('source_ranges',[])
                        for i,left in enumerate(ranges):
                            for right in ranges[i+1:]:
                                self.assertFalse(subset(left,right) or subset(right,left),(mode,left,right))
    def test_only_strictly_covered_range_metadata_is_removed(self):
        from tools.agent_memory_runtime.context_budget import deduplicate_source_ranges
        base={'symbol':'work','start_line':2,'end_line':5}
        rich={**base,'selection_reason':'event_owner','focus_line':3}
        conflict={**base,'selection_reason':'separate_reason','focus_line':4}
        other={**base,'symbol':'different'}
        h={'code_anchors':[{'source_ranges':[base,rich,conflict,other], 'source_excerpts':[{'content':'exact source'}]}],
           'path_context':{'path_candidates':[{'path_id':'p','uncertainty':['unresolved']}], 'graph_revision':1},
           'log_anchors':[{'message_template':'real event'}]}
        old=copy.deepcopy(h)
        deduplicate_source_ranges(h)
        self.assertEqual([rich,conflict,other],h['code_anchors'][0]['source_ranges'])
        self.assertEqual(old['path_context'],h['path_context'])
        self.assertEqual(old['log_anchors'],h['log_anchors'])
        self.assertEqual(old['code_anchors'][0]['source_excerpts'],h['code_anchors'][0]['source_excerpts'])
        # Unknown/invalid bounds are not folded, even if superficially equal.
        invalid={'symbol':'work','start_line':True,'end_line':5}
        h={'code_anchors':[{'source_ranges':[invalid,dict(invalid)]}]}
        deduplicate_source_ranges(h)
        self.assertEqual(2,len(h['code_anchors'][0]['source_ranges']))

    def test_reverse_order_and_unique_range_evidence_are_preserved(self):
        from tools.agent_memory_runtime.context_budget import deduplicate_source_ranges
        base={'symbol':'run','start_line':3,'end_line':7}
        rich={**base,'selection_reason':'actual_owner'}
        different_span={**base,'end_line':8}
        distinct_metadata={**base,'freshness':{'current':True}}
        numeric_metadata={**base,'freshness':{'current':1}}
        ranges=[rich,base,dict(rich),different_span,distinct_metadata,numeric_metadata]
        anchor={'source_ranges':ranges,'source_digest':'retained','source_excerpts':[{'content':'body one'},{'content':'body two'}]}
        h={'code_anchors':[anchor]}
        deduplicate_source_ranges(h)
        self.assertEqual([rich,different_span,distinct_metadata,numeric_metadata],anchor['source_ranges'])
        self.assertEqual('retained',anchor['source_digest'])
        self.assertEqual([{'content':'body one'},{'content':'body two'}],anchor['source_excerpts'])
