# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Actual ArkTS imports/calls, not injected graph rows or incident logs."""
import json
from pathlib import Path
import tempfile
from agent_memory_test_base import AgentMemoryTestBase


class QualifiedGraphProtectionTests(AgentMemoryTestBase):
    def test_real_import_and_typed_call_survive_member_exclusion(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            sources = {
                'src/model/StateModel.ets': 'export class StateModel {\n  ready: boolean = false\n  reset() { this.ready = false }\n}\n',
                'src/views/ControlPanel.ets': "import { StateModel } from '../model/StateModel'\n\n@Component\nstruct ControlPanel {\n  private state: StateModel = new StateModel()\n  build() { Text('Controls') }\n  clear() { this.state.reset() }\n}\n",
            }
            for name, text in sources.items():
                path = project / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)
            self.run_memory(project, 'learn-path', '--path', 'src')
            before = self.list_records(project, 'memory-edge')
            self.assertTrue(any(e['relation'] == 'imports' for e in before))
            self.assertTrue(any(e['relation'] == 'calls' for e in before))
            outputs = []
            for query in ('control panel rendering',
                          'control panel rendering; exclude StateModel.reset.',
                          'control panel rendering; exclude StateModel.',
                          'Locate ControlPanel.build; exclude StateModel.reset.'):
                result = self.run_memory(project, 'context', '--query', query, '--json')
                data = json.loads(result.stdout)
                self.assertTrue(any(e['relation'] == 'imports' for e in data['edge_matches']))
                self.assertIn('src/model/StateModel.ets', [a['file_path'] for a in data['query_handoff']['code_anchors']])
                outputs.append(data)
            self.assertEqual(before, self.list_records(project, 'memory-edge'))
            self.assertEqual(outputs[0]['query_handoff']['code_anchors'], outputs[1]['query_handoff']['code_anchors'])
