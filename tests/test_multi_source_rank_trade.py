# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import copy,json,tempfile,unittest
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.context_source_recovery import recover_partial_primary,RANK_REASONS
from tools.agent_memory_runtime.performance_scoring import estimate_payload_tokens
D=Path(__file__).resolve().parents[1]/'docs/evidence/multi-source-recovery'
M=json.loads((D/'length-matrix-protocol.json').read_text())

class MultiSourceTradeTests(unittest.TestCase):
    def test_all_sources_and_nonranking_facts_preserved(self):
        for variant in M:
            before=json.loads((D/f"length-{variant['count']}-before.json").read_text())
            with tempfile.TemporaryDirectory() as d:
                for name,source in variant['protocol']['sources'].items():(Path(d)/name).write_text(source)
                original=copy.deepcopy(before['compact'])
                result=recover_partial_primary(original,d,1500,source_rows=before['raw']['wiki_matches'])
                self.assertIsNot(result,original)
                self.assertEqual(before['compact'],original)
                actual=copy.deepcopy(result);expected=copy.deepcopy(original)
                for row in [expected['query_handoff']['callable_evidence']['primary'],*expected['query_handoff']['callable_evidence']['alternatives']]:
                    row.pop('score',None);row.pop('evidence_score',None)
                    row['reasons']=[r for r in row['reasons'] if r not in RANK_REASONS]
                for payload in [actual,expected]:
                    anchor=next(a for a in payload['query_handoff']['code_anchors'] if a['file_path']=='ByteFormatter.ts')
                    anchor.pop('source_excerpts');payload['query_handoff']['source_excerpt_policy'].pop('excerpt_chars');payload.pop('output_budget')
                self.assertEqual(expected,actual)
                anchor=result['query_handoff']['code_anchors'][1]
                self.assertFalse(anchor['source_excerpts'][0]['truncated'])
                self.assertIn('return output.toUpperCase()',anchor['source_excerpts'][0]['content'])
                self.assertLessEqual(estimate_payload_tokens(result),1500)
                self.assertEqual(sum(len(e['content']) for a in result['query_handoff']['code_anchors'] for e in a.get('source_excerpts',[])),result['query_handoff']['source_excerpt_policy']['excerpt_chars'])

class MultiSourcePublicTests(AgentMemoryTestBase):
    def test_explicit_multiple_sources_keep_roles_and_complete_selected_body(self):
        p=M[0]['protocol']
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for name,source in p['sources'].items():(root/name).write_text(source)
            self.run_memory(root,'init');self.run_memory(root,'learn-path','--path','.')
            out=json.loads(self.run_memory(root,'context','--query',p['query'],'--compact','--json').stdout)
            anchors=out['query_handoff']['code_anchors']
            self.assertEqual(set(p['sources']),{a['file_path'] for a in anchors})
            self.assertTrue(all(a['role']=='primary' for a in anchors))
            target=next(a for a in anchors if a['file_path']=='ByteFormatter.ts')
            self.assertIn('return output.toUpperCase()',target['source_excerpts'][0]['content'])
            self.assertFalse(target['source_excerpts'][0]['truncated'])
