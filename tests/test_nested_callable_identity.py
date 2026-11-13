# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json
import tempfile
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase

SOURCE='''import { PreferenceApi } from '../services/PreferenceApi'

@Entry
@Component
export struct PreferenceEditor {
  @State alias: string = ''
  private api: PreferenceApi = new PreferenceApi()
  commitPreference(): void {
    if (this.alias.trim().length === 0) {
      promptAction.showToast({ message: 'Alias required' })
      return
    }
    this.api.dispatchUpdate(this.alias)
  }
  build() {}
}
'''
class NestedCallableIdentityTests(AgentMemoryTestBase):
    def test_public_projected_callable_does_not_borrow_component_identity(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'src/pages').mkdir(parents=True);(root/'src/services').mkdir(parents=True);(root/'src/pages/PreferenceEditor.ets').write_text(SOURCE)
            (root/'src/services/PreferenceApi.ets').write_text("export class PreferenceApi {\n dispatchUpdate(value: string): void {\n console.info(`submit preference update ${value}`)\n }\n}\n")
            self.run_memory(root,'init');self.run_memory(root,'learn-path','--path','.')
            p=json.loads(self.run_memory(root,'context','--query','An empty alias reports an error yet submits the preference update; return the PreferenceEditor guarded page action.','--compact','--json').stdout)
            selected=[a for a in p['query_handoff']['code_anchors'] if a.get('symbol')=='commitPreference']
            self.assertTrue(selected,p['query_handoff']['code_anchors'])
            self.assertIn(selected[0].get('symbol_type'),{'method','function'})
            self.assertLessEqual(p['output_budget']['estimated_tokens'],1500)
