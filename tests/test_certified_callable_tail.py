"""Public CLI regression: certified source can be displayed without owner promotion."""
from copy import deepcopy
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest

from agent_memory_runtime.context_certified_callable_tail import extend_certified_tail

RUNTIME = Path(__file__).resolve().parents[1] / 'tools' / 'agent_memory.py'
FIXTURE = {
    'DispatchBoard.ets': """export class DispatchBoard {
  draw(): string {
    return 'Dispatch and reprint eligibility: morning or afternoon';
  }
}
""",
    'DispatchEligibility.ets': """export enum Shift {
  Closed,
  Morning,
  Afternoon,
  Cleanup
}
export class DispatchEligibility {
  canDispatch(shift: Shift, labelReady: boolean): boolean {
    if (!labelReady) {
      return false
    }
    return shift === Shift.Morning || shift === Shift.Afternoon
  }
  canReprint(shift: Shift, printerReady: boolean): boolean {
    if (!printerReady) {
      return false
    }
    return shift === Shift.Morning || shift === Shift.Afternoon
  }
}
""",
    'ShiftRoster.ets': """export class ShiftRoster {
  getDisplayTitle(): string {
    return 'Morning and afternoon dispatch and reprint schedule';
  }
}
""",
}

PAIR = "Return canDispatch and canReprint for Morning and Afternoon."
CROSS = "Show DispatchBoard.draw and DispatchEligibility.canReprint, both methods."


class CertifiedCallableTailTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root = Path(cls.tmp.name) / 'source'
        (cls.root / 'src').mkdir(parents=True)
        for name, source in FIXTURE.items():
            (cls.root / 'src' / name).write_text(source, encoding='utf-8')
        cls.cli('init')
        cls.cli('learn-path', '--path', 'src', '--replace', '--json')
        cls.raw = cls.query(PAIR)
        cls.default = cls.query(PAIR, '--compact')

    @classmethod
    def cli(cls, command, *args):
        return subprocess.check_output(
            [sys.executable, str(RUNTIME), command, '--project', str(cls.root),
             '--memory-home', str(cls.root.parent / 'home'), *args],
            text=True, timeout=25, env={**os.environ, 'PYTHONHASHSEED': '1'},
        )

    @classmethod
    def query(cls, query, *args):
        return json.loads(cls.cli('context', '--query', query, '--json', *args))

    def test_additive_complete_two_callable_display_at_default(self):
        evidence = self.raw['query_handoff']['callable_evidence']
        self.assertEqual(evidence['certainty'], 'uncertain')
        self.assertIn('certified_same_owner_callable_bounds',
                      evidence['passage_portfolio']['selection_basis'])
        h = self.default['query_handoff']
        a = h['code_anchors'][0]
        self.assertEqual(h['callable_evidence']['certainty'], 'uncertain')
        self.assertEqual([a['file_path'] for a in h['code_anchors']], [
            'src/DispatchEligibility.ets', 'src/DispatchBoard.ets', 'src/ShiftRoster.ets'])
        self.assertEqual(a['source_ranges'], [
            dict(symbol='canDispatch', start_line=8, end_line=13),
            dict(symbol='canReprint', start_line=14, end_line=19)])
        self.assertEqual(a['read_window'], dict(start_line=8, end_line=19))
        body = a['source_excerpts'][0]
        self.assertEqual((body['start_line'], body['end_line']), (6, 19))
        self.assertEqual(body['content'], '\n'.join(FIXTURE['DispatchEligibility.ets'].splitlines()[5:19]))
        self.assertTrue(body['truncated'])  # The enclosing lexical excerpt remains a partial window.
        self.assertLessEqual(self.default['output_budget']['estimated_tokens'], 1500)

    def test_explicit_default_has_the_same_additive_behavior(self):
        self.assertEqual(self.default, self.query(PAIR, '--compact', '--compact-token-budget', '1500'))

    def test_cross_file_scope_is_not_collapsed(self):
        h = self.query(CROSS, '--compact')['query_handoff']
        self.assertEqual({a['file_path'] for a in h['code_anchors']},
                         {'src/DispatchEligibility.ets', 'src/DispatchBoard.ets'})
        a = h['code_anchors'][0]
        self.assertIn(dict(symbol='canReprint', start_line=14, end_line=19), a['source_ranges'])
        w = a['read_window']
        self.assertTrue(w['start_line'] <= 14 < 19 <= w['end_line'])

    def test_projection_fails_closed_on_malformed_stale_or_over_budget(self):
        baseline = deepcopy(self.default)
        h = baseline['query_handoff']
        a = h['code_anchors'][0]
        a['source_ranges'].pop()
        a['read_window']['end_line'] = 13
        body = a['source_excerpts'][0]
        body['end_line'] = 17
        body['content'] = '\n'.join(body['content'].splitlines()[:-2])
        evidence = self.raw['query_handoff']['callable_evidence']
        rows = self.raw['wiki_matches']

        def attempt(payload=baseline, proof=evidence, source_rows=rows):
            return extend_certified_tail(payload, str(self.root), 1500, evidence=proof, source_rows=source_rows)

        self.assertEqual(attempt()['query_handoff']['code_anchors'], self.default['query_handoff']['code_anchors'])
        wrong = [{**r, 'source_digest': 'a' * 64} for r in rows]
        self.assertIs(attempt(source_rows=wrong), baseline)
        malformed = deepcopy(evidence)
        malformed['passage_portfolio']['members'][0]['source_range']['callable_end_line'] = 18
        self.assertIs(attempt(proof=malformed), baseline)
        oversized = deepcopy(baseline)
        oversized['conflict_notes'] = ['protected context detail ' * 50]
        self.assertIs(attempt(payload=oversized), oversized)
