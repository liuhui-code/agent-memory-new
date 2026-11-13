# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json
import tempfile
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase

SOURCES = {'FlagStore.ts': 'export class FlagStore {\n'
                 '  flags: boolean[] = [false, false, false];\n'
                 '  setAt(index: number, value: boolean): void {\n'
                 '    this.flags[index] = value;\n'
                 '  }\n'
                 '}\n',
 'LaneController.ts': 'export class LaneController {\n'
                      '  flags: boolean[] = [false, false, false];\n'
                      '  onClick(index: number): void {\n'
                      '    this.flags[index] = !this.flags[index];\n'
                      '    if (index + 1 < this.flags.length) {\n'
                      '      this.flags[index + 1] = this.flags[index];\n'
                      '    }\n'
                      '  }\n'
                      '}\n',
 'SplitController.ts': 'export class SplitController {\n'
                       '  selected: boolean = false;\n'
                       '  flags: boolean[] = [false, false, false];\n'
                       '  onClick(): void {\n'
                       '    this.selected = !this.selected;\n'
                       '  }\n'
                       '  saveAt(index: number, value: boolean): void {\n'
                       '    this.flags[index] = value;\n'
                       '  }\n'
                       '}\n',
 'TileWidget.ts': 'export class TileWidget {\n'
                  '  selected: boolean = false;\n'
                  '  onClick(): void {\n'
                  '    this.selected = !this.selected;\n'
                  '  }\n'
                  '}\n'}
QUERIES = ['Clicking a tile should propagate selection to adjacent tiles. Locate the complete '
 'event-to-collection mutation owner.',
 'A tile click toggles only one item instead of neighboring entries; return the handler '
 'that writes the indexed collection.',
 '点击方块后选择状态没有传播到相邻项，请只返回同时拥有事件和集合写入的源码。',
 'Locate TileWidget.onClick source.',
 'Locate FlagStore.setAt source.',
 'Locate SplitController.onClick source.']

class CollectionOwnerPublicTests(AgentMemoryTestBase):
    def test_frozen_owner_and_explicit_controls(self):
        for suffix in ('.ts', '.ets'):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                for name, text in SOURCES.items():
                    (root / (Path(name).stem + suffix)).write_text(text)
                self.run_memory(root, 'init')
                self.run_memory(root, 'learn-path', '--path', '.')
                expected = ['LaneController'] * 3 + ['TileWidget', 'FlagStore', 'SplitController']
                for query, owner in zip(QUERIES, expected):
                    with self.subTest(suffix=suffix,query=query):
                        payload = json.loads(self.run_memory(root, 'context', '--compact', '--query', query, '--json').stdout)
                        paths = {a['file_path'] for a in payload['query_handoff']['code_anchors']}
                        self.assertEqual({owner + suffix}, paths)

    def test_explicit_two_owner_targets_without_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, text in SOURCES.items():
                (root / name).write_text(text.replace('onClick', 'handleTap'))
            self.run_memory(root, 'init')
            self.run_memory(root, 'learn-path', '--path', '.')
            query = QUERIES[1] + ' Also return LaneController.handleTap and TileWidget.handleTap.'
            payload = json.loads(self.run_memory(root, 'context', '--compact', '--query', query, '--json').stdout)
            paths = {a['file_path'] for a in payload['query_handoff']['code_anchors']}
            self.assertTrue({'LaneController.ts','TileWidget.ts'} <= paths, paths)
