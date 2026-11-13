# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase

SOURCE = '''export class ArchiveReporter {
  report(): void {
    console.error('ARCHIVE_EVENT_72B9 archive copy failed')
  }
  emit(message: string): void {
    console.error(message)
  }
  wrapped(): void {
    this.emit('ARCHIVE_EVENT_72B9 archive copy failed')
  }
  dynamic(id: string): void {
    console.error(`archive copy failed event=${id}`)
  }
}
'''


class OpaqueLogAdmissionTests(AgentMemoryTestBase):
    def test_public_missing_and_real_event_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / 'archive-fixture'
            project.mkdir()
            (project / 'ArchiveReporter.ts').write_text(SOURCE)
            self.run_memory(project, 'init')
            self.run_memory(project, 'learn-path', '--path', 'ArchiveReporter.ts', '--json')
            cases = [
                ('Locate archive copy failure MISSING_EVENT_83C7', False),
                ('定位归档失败 MISSING_EVENT_83C7 的日志和源码', False),
                ('Locate ARCHIVE_EVENT_72B9 archive copy failed', True),
                ('Locate archive copy failed event=RUNTIME_EVENT_64D2', True),
                ('Find ArchiveReporter.report and MISSING_EVENT_83C7', True),
            ]
            outputs = []
            for query, present in cases:
                for compact in (False, True):
                    args = ['context', '--query', query, '--json']
                    if compact:
                        args.append('--compact')
                    payload = json.loads(self.run_memory(project, *args).stdout)
                    handoff = payload['query_handoff']
                    outputs.append({'query': query, 'compact': compact, 'payload': payload})
                    with self.subTest(query=query, compact=compact):
                        anchors = handoff.get('code_anchors', []) + handoff.get('log_anchors', [])
                        self.assertEqual(present, bool(anchors), handoff)
            Path('docs/evidence/opaque-rebuild/latest-public.json').write_text(json.dumps(outputs, ensure_ascii=False, indent=2))
