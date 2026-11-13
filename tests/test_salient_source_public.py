# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json
import tempfile
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase

SOURCES = {'.preview/cache/src/ui/RestoreView.ets': '@Component\n'
                                          'struct RestoreView {\n'
                                          '  @State retryAllowed: boolean = false\n'
                                          "  @State statusMessage: string = ''\n"
                                          '  enableRecovery(): void {\n'
                                          '    this.retryAllowed = true\n'
                                          "    this.statusMessage = 'capacity recovery "
                                          "available'\n"
                                          '  }\n'
                                          '  build() {\n'
                                          "    Button('Restore capacity').onClick(() => "
                                          'this.enableRecovery())\n'
                                          '    Text(this.statusMessage)\n'
                                          '  }\n'
                                          '}\n',
 'src/cache/IconStore.ets': 'export class IconStore {\n'
                            '  private entries: Map<string, string> = new Map()\n'
                            '  saveIcon(key: string, payload: string): void {\n'
                            '    this.entries.set(key, payload)\n'
                            '    if (this.entries.size > 8) {\n'
                            '      const first = this.entries.keys().next().value\n'
                            '      this.entries.delete(first)\n'
                            '    }\n'
                            '  }\n'
                            '}\n',
 'src/examples/IconStoreExample.ets': "import { IconStore } from '../cache/IconStore'\n"
                                      'export function demonstrateIconStore(): void {\n'
                                      '  const store = new IconStore()\n'
                                      "  store.saveIcon('alpha', 'one')\n"
                                      "  store.saveIcon('beta', 'two')\n"
                                      '}\n',
 'src/services/NoticeService.ets': 'export class NoticeService {\n'
                                   '  updateNotice(): void {\n'
                                   "    console.info('notice update dispatched')\n"
                                   '  }\n'
                                   '}\n',
 'src/storage/IncidentalNotice.ets': 'export class IncidentalNotice {\n'
                                     '  describeSnapshot(): string {\n'
                                     "    return 'archival_key'\n"
                                     '  }\n'
                                     '}\n',
 'src/storage/LiteralCatalog.ets': 'export function readArchiveDiagnostic(): string {\n'
                                   "  return 'icon_archive_corrupt'\n"
                                   '}\n',
 'src/ui/NoticePreferences.ets': 'import { NoticeService } from '
                                 "'../services/NoticeService'\n"
                                 'export class NoticePreferences {\n'
                                 '  service: NoticeService = new NoticeService()\n'
                                 '  save(): void {\n'
                                 '    this.service.updateNotice()\n'
                                 '  }\n'
                                 '}\n',
 'src/ui/RestoreView.ets': '@Component\n'
                           'struct RestoreView {\n'
                           '  @State retryAllowed: boolean = false\n'
                           "  @State statusMessage: string = ''\n"
                           '  enableRecovery(): void {\n'
                           '    this.retryAllowed = true\n'
                           "    this.statusMessage = 'capacity recovery available'\n"
                           '  }\n'
                           '  build() {\n'
                           "    Button('Restore capacity').onClick(() => "
                           'this.enableRecovery())\n'
                           '    Text(this.statusMessage)\n'
                           '  }\n'
                           '}\n',
 'src/ui/RetryBadge.ets': '@Component\n'
                          'struct RetryBadge {\n'
                          '  @State shown: boolean = false\n'
                          '  build() {\n'
                          "    Button('Retry status').onClick(() => this.shown = true)\n"
                          '  }\n'
                          '}\n'}
QUERIES = ['图标池超过容量后没有删除最早键，请返回检查 size、读取首个 key 并 delete 的正式实现，排除示例代码。',
 'Return the production icon implementation that checks size and deletes the first key. '
 'Also locate `archival_key`.',
 'Locate the caller and emitter of the ordinary log message notice update dispatched.']

class SalientSourcePublicTests(AgentMemoryTestBase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        for name,text in SOURCES.items():
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
        self.run_memory(self.root,'init')
        self.run_memory(self.root,'learn-path','--path','.')
    def tearDown(self):
        self.temp.cleanup()
    def context(self,query,compact=False):
        args=['context','--query',query,'--json']+(['--compact'] if compact else [])
        return json.loads(self.run_memory(self.root,*args).stdout)['query_handoff']
    def test_redundant_literal_retraction_keeps_real_owner_and_body(self):
        for compact in (False,True):
            h=self.context(QUERIES[0],compact)
            self.assertEqual({'src/cache/IconStore.ets'},{a['file_path'] for a in h['code_anchors']})
            if compact:
                body=' '.join(e['content'] for a in h['code_anchors'] for e in a.get('source_excerpts',[]))
                self.assertIn('.delete(',body)
                self.assertIn('.size',body)
    def test_novel_zero_method_literal_remains_raw_evidence(self):
        paths={a['file_path'] for a in self.context(QUERIES[1])['code_anchors']}
        self.assertTrue({'src/cache/IconStore.ets','src/storage/IncidentalNotice.ets'} <= paths)
    def test_explicit_literal_and_named_second_target_survive_compact(self):
        query='Locate the literal `archival_key` in IncidentalNotice.describeSnapshot and return IconStore.saveIcon source as well.'
        paths={a['file_path'] for a in self.context(query,True)['code_anchors']}
        self.assertTrue({'src/cache/IconStore.ets','src/storage/IncidentalNotice.ets'} <= paths)
    def test_plain_template_preserves_wrapper_and_emitter(self):
        h=self.context(QUERIES[2],True)
        self.assertTrue({'src/services/NoticeService.ets','src/ui/NoticePreferences.ets'} <= {a['file_path'] for a in h['code_anchors']})
        self.assertTrue(any(a.get('evidence_class')=='static_wrapped' for a in h['log_anchors']))
    def test_two_same_mechanism_entities_survive_without_both_or_qualified_names(self):
        path=self.root/'src/cache/ArchiveIconStore.ets'
        path.write_text(SOURCES['src/cache/IconStore.ets'].replace('IconStore','ArchiveIconStore'))
        self.run_memory(self.root,'learn-path','--path','.')
        query='Compare the main icon store against the archival icon store for set, size, keys and delete behavior.'
        for compact in (False,True):
            paths={a['file_path'] for a in self.context(query,compact)['code_anchors']}
            self.assertTrue({'src/cache/IconStore.ets','src/cache/ArchiveIconStore.ets'} <= paths)
