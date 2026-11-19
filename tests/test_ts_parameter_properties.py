import json
import tempfile
from pathlib import Path

from tests.agent_memory_test_base import AgentMemoryTestBase


TARGET = """export class Store {
  async read(): Promise<void> {}
}
export default class OtherStore {
  async read(): Promise<void> {}
}
"""
OWNER = """import { Store } from './Store';
export class Inbox {
  constructor(private readonly store: Store) {}
  async open(): Promise<void> {
    await this.store.read();
  }
}
"""


class TypeScriptParameterPropertyTests(AgentMemoryTestBase):
    def test_public_graph_binds_only_verified_instance_receivers(self):
        variants = {
            'Inbox': (OWNER, True),
            'SplitHeader': (OWNER.replace('private readonly store: Store',
                            '\n    ignored: string,\n    readonly store: Store,\n  '), True),
            'Plain': (OWNER.replace('private readonly store', 'store'), False),
            'Mutable': (OWNER.replace('private readonly store', 'public store'), False),
            'Shadow': (OWNER.replace('await this.store.read()', 'const store = { read() {} };\n    await store.read()'), False),
            'Static': (OWNER.replace('async open', 'static async open'), False),
            'Nested': (OWNER.replace('await this.store.read()', 'async function nested() { await this.store.read(); }'), False),
            'Duplicate': (OWNER.replace('  async open', '  private store = {}\n  async open'), False),
            'Computed': (OWNER.replace('  async open', "  ['store'] = {}\n  async open"), False),
            'Reassigned': (OWNER.replace('Store) {}', 'Store) { this.store = new Store(); }'), False),
            'BracketWrite': (OWNER.replace('Store) {}', 'Store) { this["store"] = new Store(); }'), False),
            'Complex': (OWNER.replace('store: Store)', 'store: Store | undefined)'), False),
            'Overloaded': (OWNER.replace('  constructor', '  constructor(store: Store);\n  constructor'), False),
            'DefaultImport': (OWNER.replace('import { Store }', 'import Store'), False),
            'LocalType': (OWNER.replace("import { Store } from './Store';",
                                        "import { Store } from './Store';\ntype Store = {};"), False),
            'GenericType': (OWNER.replace('class Inbox', 'class Inbox<Store>'), False),
        }
        with tempfile.TemporaryDirectory() as work:
            root = Path(work)
            (root / 'Store.ts').write_text(TARGET)
            for name, (source, _) in variants.items():
                (root / (name + '.ts')).write_text(source.replace('Inbox', name))
            (root / 'ArkOwner.ets').write_text(OWNER.replace('Inbox', 'ArkOwner'))
            self.run_memory(root, 'init')
            self.run_memory(root, 'learn-path', '--path', '.')
            symbols = json.loads(self.run_memory(root, 'list', '--type', 'code-symbol',
                                                 '--limit', '300', '--json').stdout)
            edges = json.loads(self.run_memory(root, 'list', '--type', 'memory-edge',
                                               '--limit', '1000', '--json').stdout)
            by_id = {item['id']: item['qualified_name'] for item in symbols}
            observed = {
                (by_id[edge['source_id']], edge['relation'])
                for edge in edges
                if edge['source_type'] == edge['target_type'] == 'code_symbol'
                and by_id.get(edge['target_id']) in {'Store.read', 'OtherStore.read'}
                and edge['relation'] in {'calls', 'awaits'}
            }
            expected = {(name + '.open', relation) for name, (_, allowed) in variants.items()
                        if allowed for relation in ('calls', 'awaits')}
            self.assertEqual(expected, observed)
            for edge in edges:
                if (by_id.get(edge['source_id']) == 'Inbox.open' and by_id.get(edge['target_id']) == 'Store.read'
                        and edge['source_type'] == edge['target_type'] == 'code_symbol'):
                    evidence = json.loads(edge['evidence'])
                    self.assertEqual(5, evidence['line'])
                    self.assertEqual('static', evidence['evidence_class'])
                    self.assertEqual(64, len(evidence['source_digest']))
