# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime import log_effects

FIXTURE = Path(__file__).parent / 'fixtures' / 'rebuilt-sink-literal'


class RebuiltSinkLiteralTests(AgentMemoryTestBase):
    def test_frozen_public_messages_keep_paths_and_complete_bodies(self):
        manifest = json.loads((FIXTURE / 'manifest.json').read_text())
        frozen = json.loads((FIXTURE / 'freeze.json').read_text())
        self.assertEqual(frozen['files']['manifest.json'],
                         hashlib.sha256((FIXTURE / 'manifest.json').read_bytes()).hexdigest())
        with tempfile.TemporaryDirectory() as directory:
            for case in manifest['cases']:
                with self.subTest(case=case['id']):
                    source = FIXTURE / case['source']
                    self.assertEqual(case['source_sha256'], hashlib.sha256(source.read_bytes()).hexdigest())
                    project = Path(directory) / case['id']
                    project.mkdir()
                    shutil.copy2(source, project / source.name)
                    self.run_memory(project, 'init')
                    self.run_memory(project, 'wiki-index')
                    for mode in ((), ('--compact',)):
                        handoff = json.loads(self.run_memory(
                            project, 'context', '--query', case['query'], *mode, '--json',
                        ).stdout)['query_handoff']
                        wrapped = [a for a in handoff['log_anchors']
                                   if a.get('function') == 'run'
                                   and a.get('evidence_class') == 'static_wrapped']
                        self.assertEqual(1, len(wrapped))
                        # Preserve and report this separate unresolved binding defect.
                        expected = ('east-region' if case['id'] == 'second_message_parameter'
                                    else case['expected_effect_static_template'])
                        self.assertEqual(expected, wrapped[0]['message_template'])
                        self.assertEqual(case['expected_static_call_path'], wrapped[0]['call_path'])
                        self.assertEqual(1, wrapped[0]['wrapper_depth'])
                        self.assertFalse(wrapped[0]['truncated'])
                        self.assertEqual(['CatalogService.ts#run', 'CatalogService.ts#refresh',
                                          'CatalogService.ts#logger.info'], wrapped[0]['call_path_locations'])
                        if not mode:  # Raw anchors do not promise inline source bodies.
                            continue
                        lines = source.read_text().splitlines()
                        excerpts = [e for a in handoff['code_anchors']
                                    if a['file_path'] == source.name
                                    for e in a.get('source_excerpts', [])]
                        self.assertTrue(excerpts)
                        for e in excerpts:
                            self.assertEqual('\n'.join(lines[e['start_line'] - 1:e['end_line']]), e['content'])
                        for name, span in case['required_source_ranges'].items():
                            self.assertTrue(any(e['start_line'] <= span['start_line']
                                                and e['end_line'] >= span['end_line']
                                                for e in excerpts), name)

    def test_literal_proof_rejects_composition_and_unsafe_argument_positions(self):
        positives = [("Logger.info('fixed')", 'fixed'), ('Logger.info("fixed, value")', 'fixed, value'),
                     ("Logger.info('')", ''), ("Logger.info('{message}')", '{message}'),
                     ('Logger.info(`fixed`)', 'fixed'), ('Logger.info(`prefix ${bucket}`)', 'prefix ${bucket}'),
                     ('console.error(`prefix ${this.bucket}`)', 'prefix ${this.bucket}'),
                     (r"Logger.info('it\'s fixed')", r"it\'s fixed"),
                     ("hilog.info(0x1200, 'TAG', 'actual message')", 'actual message')]
        negatives = [('Logger.info(message)', '{message}'), ("Logger.info('prefix' + message)", 'prefix'),
                     ("Logger.info(('fixed'))", 'fixed'), ("Logger.info('fixed' as string)", 'fixed'),
                     ("Logger.info(flag ? 'yes' : 'no')", 'yes'), ("Logger.info(format('value'))", 'value'),
                     ('Logger.info(`prefix ${format(message)}`)', 'prefix ${format(message)}'),
                     ('Logger.info(`prefix ${a[0]}`)', 'prefix ${a[0]}'),
                     ('Logger.info(`prefix ${flag ? a : b}`)', 'prefix ${flag ? a : b}'),
                     ('Logger.info(`prefix ${{a: b}}`)', 'prefix ${{a: b}}'),
                     ('Logger.info(`prefix ${`nested`}`)', 'prefix ${'),
                     ('Logger.info(`broken ${message`)', 'broken ${message'),
                     ("Logger.info('fixed')", 'stale template'),
                     ("systemLog.info(0, 'TAG', 'fixed')", 'fixed'),
                     ("hilog.info(0 /* , */ , 'TAG', message)", 'TAG'),
                     ("hilog.info(/,/.source, 'TAG', message)", 'TAG'),
                     ("hilog.info(call<A, B>(), 'TAG', message)", 'TAG'),
                     ("hilog.info(0, 'TAG', message)", '{message}'),
                     (r"Logger.info('ending\\')", '{value}'), ('hilog.info(0)', ''), ('Logger.info()', ''), ('', '')]
        for expected, cases in ((True, positives), (False, negatives)):
            for raw, template in cases:
                with self.subTest(raw=raw, template=template):
                    self.assertEqual(expected, log_effects.has_source_literal_message({
                        'sink_file_path': 'Writer.ts', 'sink_statement': raw, 'sink_template': template}))
        self.assertFalse(log_effects.has_source_literal_message({
            'sink_file_path': 'writer.py', 'sink_statement': "logger.info('fixed')", 'sink_template': 'fixed'}))

    def test_empty_placeholder_and_dynamic_messages_keep_source_kind(self):
        cases = [("''", ''), ("'{message}'", '{message}'), ('message', 'caller value'),
                 ("'prefix ' + message", 'caller value'), ('`prefix ${format(message)}`', 'caller value')]
        with tempfile.TemporaryDirectory() as directory:
            for number, (expression, expected) in enumerate(cases):
                with self.subTest(expression=expression):
                    project = Path(directory) / f'case-{number}'
                    project.mkdir()
                    (project / 'Writer.ts').write_text(
                        'export class Writer {\n  emit(message: string) {\n'
                        f'    Logger.info({expression})\n  }}\n'
                        "  run() {\n    this.emit('caller value')\n  }\n}\n")
                    self.run_memory(project, 'init')
                    self.run_memory(project, 'wiki-index')
                    with sqlite3.connect(self.project_memory_dir(project) / 'memory.db') as conn:
                        rows = conn.execute("SELECT message_template FROM code_log_effects WHERE function = 'run'").fetchall()
                    self.assertEqual([(expected,)], rows)
