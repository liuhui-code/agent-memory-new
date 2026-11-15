# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json, tempfile
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase

D=Path(__file__).parents[1]/'docs/evidence'
P=json.loads((D/'cache-eviction-current/protocol.json').read_text())
B=json.loads((D/'cache-positive-scan-current/before.json').read_text())

class CacheScanPublicTests(AgentMemoryTestBase):
    def test_unchanged_public_red_and_three_controls(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'source'; root.mkdir()
            for name,source in P['sources'].items(): (root/name).write_text(source)
            self.run_memory(root,'init'); self.run_memory(root,'learn-path','--path','.')
            for i,c in enumerate(P['queries']):
                q=c['query']; out=json.loads(self.run_memory(root,'context','--query',q,'--compact','--json').stdout)
                h=out['query_handoff']
                if i==0:
                    self.assertEqual([a['file_path'] for a in h['code_anchors']],['ExpiryStore.ts'])
                    e=h['code_anchors'][0]['source_excerpts'][0]
                    self.assertEqual((e['start_line'],e['end_line']),(3,14)); self.assertFalse(e['truncated'])
                    self.assertEqual(e['content'],'\n'.join(P['sources']['ExpiryStore.ts'].splitlines()[2:14]))
                    self.assertIsNone(h['callable_evidence']['primary'])
                    self.assertIn('timestamp_unproven',h['callable_evidence']['boundary'])
                else:
                    before=B['public'][q]['compact']['query_handoff']
                    self.assertEqual(h['callable_evidence'],before['callable_evidence'])
                    self.assertEqual(h['code_anchors'],before['code_anchors'])
                self.assertLessEqual(out['output_budget']['estimated_tokens'],1500)

    def test_public_multiple_positive_scan_bodies(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'source'; root.mkdir()
            names=['ExpiryStore','SecondStore','ThirdStore']
            for name in names:
                (root/(name+'.ts')).write_text(P['sources']['ExpiryStore.ts'].replace('ExpiryStore',name))
            (root/'ArrivalPool.ts').write_text(P['sources']['ArrivalPool.ts'])
            (root/'CacheMonitor.ts').write_text(P['sources']['CacheMonitor.ts'])
            self.run_memory(root,'init'); self.run_memory(root,'learn-path','--path','.')
            out=json.loads(self.run_memory(root,'context','--query',P['queries'][0]['query'],'--compact','--json').stdout)
            anchors=out['query_handoff']['code_anchors']
            self.assertEqual({a['file_path'] for a in anchors},{name+'.ts' for name in names})
            self.assertTrue(all(any(e['start_line']==3 and e['end_line']==14 and not e['truncated']
                                   for e in a.get('source_excerpts',[])) for a in anchors))
            self.assertLessEqual(out['output_budget']['estimated_tokens'],1500)
