"""Fixed self-contained Development sources through the ordinary public CLI."""
import json, tempfile, unittest
from pathlib import Path
from tests.command_table_test_support import prepare, cli, snapshot_database, restore_database
from tests.test_ui_divider_selection import ordinary
from tools.agent_memory_runtime.storage import connect
from tools.agent_memory_runtime.context_record_loop_transaction import restore_whitelist

P = json.loads((Path(__file__).parent/'fixtures/ui_divider.json').read_text())


class DividerPublic(unittest.TestCase):
    def test_fixed_twenty_four_requests(self):
        count = 0
        for cohort, sources in P['sources'].items():
            with tempfile.TemporaryDirectory() as t:
                project = prepare(t, sources=sources); saved = snapshot_database(project)
                try:
                    with connect(project) as db:
                        symbols = {r['id']: dict(r) for r in db.execute('SELECT * FROM code_symbols')}
                    for case in [c for c in P['cases'] if c['cohort'] == cohort]:
                        with self.subTest(case=case['id']):
                            q = case['query']; restore_database(project, saved)
                            baseline, compact, pool = ordinary(project, q)
                            restore_database(project, saved)
                            raw = json.loads(cli(project, 'context', '--query', q, '--json'))
                            restore_database(project, saved)
                            out = json.loads(cli(project, 'context', '--query', q, '--compact', '--json'))
                            self.assertEqual(raw, baseline)
                            self.assertLessEqual(out['output_budget']['estimated_tokens'], 1500)
                            if case['expected_owners'] is None:
                                self.assertEqual(out, compact)
                            else:
                                anchors = out['query_handoff']['code_anchors']
                                actual = [symbols[a['record_ids'][0]] for a in anchors]
                                self.assertCountEqual([r['owner_name'] for r in actual], case['expected_owners'])
                                for a, row in zip(anchors, actual):
                                    self.assertEqual(a['symbol_type'], row['symbol_type'])
                                    text = '\n'.join(sources[row['file_path']].splitlines()[row['start_line']-1:row['end_line']])
                                    self.assertEqual(a['source_excerpts'][0]['content'], text)
                                    self.assertFalse(a['source_excerpts'][0]['truncated'])
                                self.assertEqual(restore_whitelist(out, compact), compact)
                                self.assertIsNone(out['query_handoff']['callable_evidence']['primary'])
                        count += 1
                finally:
                    saved.close()
        self.assertEqual(count, 24)

if __name__ == '__main__': unittest.main()
