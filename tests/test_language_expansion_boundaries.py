# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json
import tempfile
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.text import query_tokens

class LanguageExpansionBoundaryTests(AgentMemoryTestBase):
    def protocol(self):
        return json.loads((Path(__file__).resolve().parents[1]/'docs/evidence/language-token-boundary/protocol.json').read_text())

    def test_language_trigger_ascii_identifier_boundaries(self):
        for query in self.protocol()['token_negative']:
            with self.subTest(query=query):
                self.assertFalse({'entry','ability','stage'} & set(query_tokens(query)))

    def test_real_language_and_platform_terms_keep_current_expansion(self):
        for query in self.protocol()['token_positive']:
            with self.subTest(query=query):
                self.assertTrue({'arkts','ets','entry','ability','stage'} <= set(query_tokens(query)))

    def test_public_packets_does_not_recall_unrelated_platform(self):
        protocol=self.protocol()
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for name,source in protocol['sources'].items():(root/name).write_text(source)
            self.run_memory(root,'init');self.run_memory(root,'learn-path','--path','.')
            query=protocol['queries'][0]
            out=json.loads(self.run_memory(root,'context','--query',query,'--compact','--json').stdout)
            self.assertEqual({'packet_decoder.py'},{a['file_path'] for a in out['query_handoff']['code_anchors']})
