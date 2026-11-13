# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json
import tempfile
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase

FILES = {'src/config/ExtensionManifest.ets': 'export const ExtensionManifest = {\n'
                                     "  capability: 'Runtime capability "
                                     "unavailable',\n"
                                     "  declaredExtension: 'Share',\n"
                                     '  probeRequired: true,\n'
                                     '}\n',
 'src/runtime/ExtensionInspector.ets': 'import { bundleManager } from '
                                       "'@kit.AbilityKit'\n"
                                       'export class ExtensionInspector {\n'
                                       '  async inspectInstalled(): '
                                       'Promise<boolean> {\n'
                                       '    const details = await '
                                       'bundleManager.getBundleInfoForSelf(0)\n'
                                       '    return '
                                       'details.extensionAbilityInfo.length > '
                                       '0\n'
                                       '  }\n'
                                       '}\n',
 'src/runtime/ProbeNotes.ets': 'export class ProbeNotes {\n'
                               '  explain(): string {\n'
                               '    return '
                               "'bundleManager.getBundleInfoForSelf(0) runtime "
                               "capability'\n"
                               '  }\n'
                               '}\n',
 'src/ui/ExtensionSettings.ets': '@Component\n'
                                 'struct ExtensionSettings {\n'
                                 '  build() {\n'
                                 '    Column() {\n'
                                 "      Text('Runtime capability inspection "
                                 "unavailable')\n"
                                 "      Text('Bundle extension capability "
                                 "query settings')\n"
                                 '    }\n'
                                 '  }\n'
                                 '}\n'}
QUERIES = ['The manifest declares a capability but runtime inspection rejects it. Locate executable runtime capability probing source.', 'Find the bundle capability query that checks an installed extension, not the settings text.', '运行时扩展能力检查不可用，请定位执行 bundle 能力探测的方法，不要返回设置页面。', 'Locate ExtensionSettings.build source.', 'Locate ExtensionInspector.inspectInstalled and ExtensionSettings.build source.']

class RuntimeCapabilityPublicTests(AgentMemoryTestBase):
    def test_executable_probe_beats_declared_and_textual_claims(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for name,text in FILES.items():
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
            self.run_memory(root,'init');self.run_memory(root,'learn-path','--path','.')
            for query in QUERIES[:3]:
                h=json.loads(self.run_memory(root,'context','--query',query,'--compact','--json').stdout)['query_handoff']
                self.assertEqual({'src/runtime/ExtensionInspector.ets'},{a['file_path'] for a in h['code_anchors']},query)
                body=' '.join(e['content'] for a in h['code_anchors'] for e in a.get('source_excerpts',[]))
                self.assertIn('bundleManager.getBundleInfoForSelf',body)
            for query,expected in [(QUERIES[3],{'src/ui/ExtensionSettings.ets'}),
                                   (QUERIES[4],{'src/ui/ExtensionSettings.ets','src/runtime/ExtensionInspector.ets'})]:
                h=json.loads(self.run_memory(root,'context','--query',query,'--compact','--json').stdout)['query_handoff']
                self.assertTrue(expected <= {a['file_path'] for a in h['code_anchors']},query)

            for query in ['Find runtime capability text.', 'Find runtime capability manifest metadata.',
                          'Locate the literal `runtime capability` in ProbeNotes.explain.',
                          'Find runtime capability source and declaration.']:
                h=json.loads(self.run_memory(root,'context','--query',query,'--compact','--json').stdout)['query_handoff']
                self.assertFalse(h.get('callable_evidence',{}).get('primary',{}).get('source_operation_match'),query)
            path=root/'src/runtime/SpareExtensionInspector.ets'
            path.write_text(FILES['src/runtime/ExtensionInspector.ets'].replace('ExtensionInspector','SpareExtensionInspector'))
            self.run_memory(root,'learn-path','--path','.')
            h=json.loads(self.run_memory(root,'context','--query',QUERIES[0],'--compact','--json').stdout)['query_handoff']
            self.assertFalse(h.get('callable_evidence',{}).get('primary',{}).get('source_operation_match'))
            # Old ambiguity stays fail-open rather than becoming a false unique proof.
            self.assertIn('src/runtime/ProbeNotes.ets',{a['file_path'] for a in h['code_anchors']})
