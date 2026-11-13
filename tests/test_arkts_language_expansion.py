# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,tempfile
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.text import query_tokens
class ArktsLanguageExpansionTests(AgentMemoryTestBase):
    def test_language_does_not_imply_lifecycle_roles(self):
        for query in ('ArkTS','ets'):
            tokens=set(query_tokens(query));self.assertTrue({'arkts','ets'}<=tokens)
            self.assertFalse(tokens & {'entry','ability','stage','harmonyos'})
    def test_platform_and_explicit_roles_remain(self):
        for query in ('鸿蒙','harmony','harmonyos'):
            self.assertTrue({'harmonyos','arkts','ets','entry','ability','stage'}<=set(query_tokens(query)))
        self.assertTrue({'ability','stage'}<=set(query_tokens('ArkTS Ability Stage')))
    def test_public_language_and_real_platform_controls(self):
        protocol=json.loads((Path(__file__).resolve().parents[1]/'docs/eval/arkts-language-topic/protocol.json').read_text())
        included={'ui-language','ui-plain','algorithm-byte-language','algorithm-byte-plain','ability','qualified','arkts-ability','platform-stage','platform-ability','language-lifecycle','ets-stage'}
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name,source in protocol['sources'].items():(root/name).write_text(source)
            self.run_memory(root,'init');self.run_memory(root,'learn-path','--path','.')
            for name,q,expected in protocol['queries']:
                if name not in included:continue
                with self.subTest(query=q):
                    out=json.loads(self.run_memory(root,'context','--query',q,'--compact','--json').stdout)['query_handoff']
                    self.assertEqual([expected],[a['file_path'] for a in out['code_anchors']])
                    text='\n'.join(e['content'] for a in out['code_anchors'] for e in a.get('source_excerpts',[]))
                    self.assertIn({'GlyphList.ets':'.divider(', 'ByteMixer.ts':'checksum << 1','EntryAbility.ets':'onWindowStage'}[expected],text)
