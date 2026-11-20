import json
from pathlib import Path
import tempfile

from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.context_ts_return_pair import read, sole_own_reference


PRODUCER = """export class RouteTable {
  async readRoute(zone: string): Promise<{label: string}> {
    return {label: zone + ' terminal'};
  }
}
"""
CONSUMER = """import { RouteTable } from './RouteTable.ts';
export class DispatchBoard {
  label = 'blank';
  constructor(private readonly table: RouteTable) {}
  async refresh(): Promise<string> {
    const next = await this.table.readRoute('south');
    USE
    return this.label;
  }
  recordLabel(value: string): void {
    ACTION
  }
}
"""
QUERY = "Why does the dispatch board display this label? Trace the returned route value into the board and show both relevant methods."


class TypeScriptReturnPairTests(AgentMemoryTestBase):
    def test_exact_call_occurrence(self):
        prefix = "const a = await this.table.readRoute('south'); const b = await this.table.readRoute('east'); "
        for var, name in [('a', 'south'), ('b', 'east')]:
            text = prefix + f'this.label = {var}.label; return this.label;'
            span, field, method, arity, slot, setter = read(text)
            self.assertEqual(text[slice(*span)], f"this.table.readRoute('{name}')")
            self.assertEqual((field, method, arity, slot, setter), ('table', 'readRoute', True, 'label', None))
        for use in ("this.label = 'cached';", "this.other = a.label;",
                    "void a.label; this.label = 'cached';",
                    "const set = () => {this.label = a.label;}; void set;"):
            self.assertIsNone(read(prefix + use + ' return this.label;'))

    def test_shared_sink_cannot_identify_request(self):
        from tools.agent_memory_runtime.source_call_scanner import code_mask
        own = CONSUMER.replace('USE', 'this.recordLabel(next.label);').replace('ACTION', 'this.label = value;')
        self.assertTrue(sole_own_reference(own, code_mask(own), 'recordLabel'))
        shared = own.rstrip().removesuffix('}') + """
  displayCondition(): string {
    this.recordLabel('unavailable');
    return this.label;
  }
}
"""
        self.assertFalse(sole_own_reference(shared, code_mask(shared), 'recordLabel'))
        computed = own.replace('this.recordLabel(next.label);', "this['recordLabel']('cached');")
        self.assertFalse(sole_own_reference(computed, code_mask(computed), 'recordLabel'))

    def test_public_append_only_and_unread_controls(self):
        for label, use, action, expected in (
            ('direct-not-primary', 'this.label = next.label;', 'this.label = value;', False),
            ('setter', 'this.recordLabel(next.label);', 'this.label = value;', True),
            ('ignores', 'this.recordLabel(next.label);', "this.label = 'cached';", False),
            ('unrelated', "void next.label; this.label = 'cached';", 'this.label = value;', False),
        ):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root/'RouteTable.ts').write_text(PRODUCER)
                (root/'DispatchBoard.ts').write_text(CONSUMER.replace('USE', use).replace('ACTION', action))
                self.run_memory(root, 'init')
                self.run_memory(root, 'learn-path', '--path', '.')
                def context(*flags):
                    result = self.run_memory(root, 'context', '--query', QUERY, '--compact', *flags, '--json')
                    return json.loads(result.stdout)
                base = context('--compact-token-budget', '1500')
                trial = context()
                if not expected:
                    self.assertEqual(trial, base)
                    continue
                h = trial['query_handoff']
                old = base['query_handoff']
                self.assertEqual(h['code_anchors'][:-1], old['code_anchors'])
                add = h['code_anchors'][-1]
                self.assertEqual((add['file_path'], add['symbol'], add['role']), ('RouteTable.ts', 'readRoute', 'expansion'))
                self.assertEqual(add['read_window'], {'start_line': 2, 'end_line': 4})
                self.assertEqual(add['source_excerpts'][0]['content'], '\n'.join(PRODUCER.splitlines()[1:4]))
                for key in old.keys() - {'code_anchors', 'source_excerpt_policy'}:
                    self.assertEqual(h[key], old[key], key)
                self.assertLessEqual(trial['output_budget']['estimated_tokens'], 1500)
                self.assertFalse(trial['output_budget']['truncated'])
                (root/'RouteTable.ts').write_text(PRODUCER + '// changed after learn\n')
                self.assertEqual(context(), context('--compact-token-budget', '1500'))
