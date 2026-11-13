# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json
import tempfile
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase

SOURCES = {'SplitPanel.ets': '@Component\n'
                   'struct SplitPanel {\n'
                   '  @Builder\n'
                   '  renderDirection() {\n'
                   "    List() { Text('direction') }\n"
                   '    .listDirection(Axis.Horizontal)\n'
                   '  }\n'
                   '  @Builder\n'
                   '  renderSize() {\n'
                   "    List() { Text('size') }\n"
                   '    .height(180)\n'
                   '  }\n'
                   '}\n',
 'StripModel.ets': 'export class StripModel {\n'
                   '  getTiles(): Tile[] {\n'
                   '    return this.tiles\n'
                   '  }\n'
                   '}\n',
 'StripPanel.ets': '@Component\n'
                   'struct StripPanel {\n'
                   '  build() {\n'
                   '    Column() {\n'
                   '      this.renderStrip()\n'
                   '    }\n'
                   '  }\n'
                   '  @Builder\n'
                   '  renderStrip() {\n'
                   '    List() {\n'
                   '      ForEach(this.tiles, (tile: Tile) => {\n'
                   '        ListItem() { TileView({ tile: tile }) }\n'
                   '      })\n'
                   '    }\n'
                   '    .listDirection(Axis.Horizontal)\n'
                   '    .height(180)\n'
                   '  }\n'
                   '}\n',
 'TileView.ets': '@Component\n'
                 'struct TileView {\n'
                 '  build() {\n'
                 '    Column() { Text(this.title) }\n'
                 '    .height(70)\n'
                 '  }\n'
                 '}\n'}
QUERIES = ['A horizontal media list clips tiles in its viewport. Locate the Builder method that '
 'owns list direction and height.',
 'Tiles are cut off in a horizontally scrolling strip; return the reusable list Builder '
 'rather than a tile or data model.',
 '横向媒体列表中的方块被裁剪，请返回设置列表方向和高度的 Builder 源码，不要返回方块或数据模型。',
 'Locate TileView.build source.',
 'Locate StripModel.getTiles source.',
 'Locate SplitPanel.renderDirection source.']

class ExactSymbolPublicTests(AgentMemoryTestBase):
    def test_builder_role_is_not_the_build_identifier(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name,text in SOURCES.items():
                (root/name).write_text(text)
            self.run_memory(root,'init')
            self.run_memory(root,'learn-path','--path','.')
            # The Chinese Builder-role query previously projected TileView.build.
            # Existing passing semantic/named controls remain separate assertions.
            for index,expected in ((1,'StripPanel.ets'),(2,'StripPanel.ets'),(4,'StripModel.ets'),(5,'SplitPanel.ets')):
                with self.subTest(query_index=index):
                    payload=json.loads(self.run_memory(root,'context','--compact','--query',QUERIES[index],'--json').stdout)
                    anchors=payload['query_handoff']['code_anchors']
                    self.assertEqual({expected},{a['file_path'] for a in anchors})
            exact=json.loads(self.run_memory(root,'context','--compact','--query',QUERIES[3],'--json').stdout)
            self.assertIn('TileView.ets',{a['file_path'] for a in exact['query_handoff']['code_anchors']})
