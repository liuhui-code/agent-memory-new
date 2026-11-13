# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json
import tempfile
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase

SOURCES = {'CallbackRegistry.ets': 'export class CallbackRegistry {\n'
                         '  removeCallback(): void {\n'
                         '    this.listeners.unregisterViewCallback(this.callback)\n'
                         '  }\n'
                         '}\n',
 'PanelAbility.ets': 'export class PanelAbility {\n'
                     '  onWindowStageDestroy(): void {\n'
                     '    this.listeners.unregisterViewCallback(this.callback)\n'
                     '  }\n'
                     '}\n',
 'PanelWidget.ets': 'export class PanelWidget {\n'
                    '  onWindowStageDestroy(): void {\n'
                    '    this.visible = false\n'
                    '  }\n'
                    '}\n',
 'SplitAbility.ets': 'export class SplitAbility {\n'
                     '  onWindowStageDestroy(): void {\n'
                     '    this.visible = false\n'
                     '  }\n'
                     '  releaseCallback(): void {\n'
                     '    this.listeners.unregisterViewCallback(this.callback)\n'
                     '  }\n'
                     '}\n'}
QUERIES = ['A listener must be unregistered before the panel context is destroyed. Locate the '
 'lifecycle cleanup owner.',
 'Panel shutdown leaves a callback registered; return the ability that owns both '
 'destruction and callback cleanup.',
 '面板上下文销毁前没有注销监听回调，请只返回同时拥有生命周期边界和清理动作的源码。',
 'Locate PanelWidget.onWindowStageDestroy source.',
 'Locate CallbackRegistry.removeCallback source.',
 'Locate SplitAbility.releaseCallback source.']

class LifecycleOwnerPublicTests(AgentMemoryTestBase):
    def test_frozen_cleanup_owner_and_named_controls(self):
        for suffix in ('.ts','.ets'):
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                for name,source in SOURCES.items():
                    (root/Path(name).with_suffix(suffix)).write_text(source)
                self.run_memory(root,'init')
                self.run_memory(root,'learn-path','--path','.')
                expected=['PanelAbility']*3+['PanelWidget','CallbackRegistry','SplitAbility']
                for query,owner in zip(QUERIES,expected):
                    with self.subTest(suffix=suffix,query=query):
                        result=json.loads(self.run_memory(root,'context','--compact','--query',query,'--json').stdout)
                        paths={a['file_path'] for a in result['query_handoff']['code_anchors']}
                        self.assertEqual({owner+suffix},paths)
                query=QUERIES[1]+' Also return PanelAbility.onWindowStageDestroy and PanelWidget.onWindowStageDestroy.'
                result=json.loads(self.run_memory(root,'context','--compact','--query',query,'--json').stdout)
                paths={a['file_path'] for a in result['query_handoff']['code_anchors']}
                self.assertTrue({'PanelAbility'+suffix,'PanelWidget'+suffix} <= paths,paths)
