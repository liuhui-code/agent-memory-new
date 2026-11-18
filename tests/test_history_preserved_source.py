# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Optional source retention does not suppress historical identifier authority."""
import json
from pathlib import Path
import tempfile
from agent_memory_test_base import AgentMemoryTestBase


class HistoryPreservedSourceTests(AgentMemoryTestBase):
    def test_history_action_and_reference_keep_sources_and_primary(self):
        repo = Path(__file__).resolve().parents[1]
        source = repo/'docs/evidence/history-action-before/source'
        queries = [
            'After an earlier load failed, replacing the document must reset its ready flag before opening the new document. Find the state owner.',
            'After an earlier load failed, replacing the document must reset its ready flag. Find the failed operation implementation.',
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ['DocumentSession.ts','ThumbnailLoader.ts']:
                (root/name).write_bytes((source/name).read_bytes())
            self.run_memory(root,'learn-path','--path','.')
            for query in queries:
                baseline=json.loads(self.run_memory(root,'context','--query',query,'--compact','--json').stdout)
                kept=json.loads(self.run_memory(root,'context','--query',query,'--compact','--preserve-selected-source-anchors','--compact-token-budget','2000','--json').stdout)
                old,new=baseline['query_handoff'],kept['query_handoff']
                self.assertEqual(old['callable_evidence']['primary'],new['callable_evidence']['primary'])
                self.assertEqual('load',new['callable_evidence']['primary']['symbol'])
                self.assertEqual(old['callable_evidence']['certainty'],new['callable_evidence']['certainty'])
                self.assertEqual(old['log_anchors'],new['log_anchors'])
                self.assertFalse(kept['output_budget']['truncated'])
                self.assertLessEqual(kept['output_budget']['estimated_tokens'],2000)
                text={a['file_path']:'\n'.join(e['content'] for e in a.get('source_excerpts',[])) for a in new['code_anchors']}
                self.assertIn('this.ready = false',text['DocumentSession.ts'])
                self.assertIn('await this.reader.openDocument(path)',text['DocumentSession.ts'])
                self.assertIn("console.error('THUMBNAIL_READ_FAILED: load failed')",text['ThumbnailLoader.ts'])
