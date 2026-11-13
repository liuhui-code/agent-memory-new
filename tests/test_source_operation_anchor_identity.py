# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import hashlib
import json
import sqlite3
import tempfile
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase

ROOT=Path(__file__).resolve().parents[1]
PROTOCOL=json.loads((ROOT/'docs/evidence/operation-anchor/protocol.json').read_text())

class SourceOperationAnchorIdentityTests(AgentMemoryTestBase):
    def test_public_anchor_matches_certified_method_and_current_source(self):
        for ext in ('.ts','.ets'):
            with tempfile.TemporaryDirectory() as d:
                root=Path(d);file=root/('RuntimeInspector'+ext);file.write_text(PROTOCOL['source'])
                self.run_memory(root,'init');self.run_memory(root,'learn-path','--path','.')
                def query(text,compact=False):
                    args=['context','--query',text,'--json']+(['--compact'] if compact else [])
                    return json.loads(self.run_memory(root,*args).stdout)['query_handoff']
                raw=query(PROTOCOL['query']);compact=query(PROTOCOL['query'],True)
                primary=raw['callable_evidence']['primary']
                self.assertEqual('inspect',primary['symbol'])
                self.assertTrue(primary['source_operation_match'])
                anchor=compact['code_anchors'][0]
                self.assertEqual('inspect',anchor['symbol'])
                self.assertEqual({'inspect'},{r['symbol'] for r in anchor['source_ranges']})
                self.assertEqual({'inspect'},{r['symbol'] for r in anchor['source_excerpts']})
                with sqlite3.connect(self.project_memory_dir(root)/'memory.db') as conn:
                    digest,start,end=conn.execute("SELECT source_digest,start_line,end_line FROM code_symbols WHERE symbol='inspect'").fetchone()
                self.assertEqual(hashlib.sha256(file.read_bytes()).hexdigest(),digest)
                self.assertEqual((start,end),(anchor['source_ranges'][0]['start_line'],anchor['source_ranges'][0]['end_line']))
                excerpt=anchor['source_excerpts'][0]
                self.assertEqual((start,end),(excerpt['start_line'],excerpt['end_line']))
                self.assertEqual('\n'.join(file.read_text().splitlines()[start-1:end]),excerpt['content'])
                label=query('Locate RuntimeInspector.label.',True)
                self.assertIn('label',{a['symbol'] for a in label['code_anchors']})

    def test_multiple_operation_owners_do_not_gain_unique_projection(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for name in ('RuntimeInspector','BackupInspector'):
                (root/(name+'.ts')).write_text(PROTOCOL['source'].replace('RuntimeInspector',name))
            self.run_memory(root,'init');self.run_memory(root,'learn-path','--path','.')
            raw=json.loads(self.run_memory(root,'context','--query',PROTOCOL['query'],'--json').stdout)['query_handoff']
            self.assertNotIn('"source_operation_match": true',json.dumps(raw))
