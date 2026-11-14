# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from tools.agent_memory_runtime.query_recovery_pair import (
    bind_from_rows, recovery_request, valid, preserve_recovery_pair, accepted_output, current_sources,
)

D = Path(__file__).resolve().parents[1] / 'docs/evidence/recovery-role-feasibility'


class RecoveryPairTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.before = json.loads((D / 'before-public.json').read_text())[0]
        self.protocol = json.loads((D / 'protocol.json').read_text())
        self.query = self.before['case']['query']
        self.rows = self.before['symbols']
        self.project = SimpleNamespace(root=self.root, project_id=self.rows[0]['project_id'])
        for name, source in self.protocol['sources'].items():
            file = self.root / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(source)
        self.handoff = self.before['raw']['query_handoff']
        self.files = [r for r in self.rows if r['symbol_type'] == 'class']

    def bound(self, handoff=None, rows=None):
        return bind_from_rows(self.project, self.query, handoff or self.handoff,
                              self.rows if rows is None else rows, self.files)

    def test_complete_request(self):
        for c in self.protocol['queries'][:3]:
            self.assertTrue(recovery_request(c['query']))
        for c in self.protocol['queries'][3:]:
            self.assertFalse(recovery_request(c['query']))
        for q in self.protocol['grammar_controls']['unknown']:
            self.assertFalse(recovery_request(q))

    def test_original_bound_and_non_erasure(self):
        bound = self.bound(); anchors = bound['code_anchors']
        self.assertTrue(valid(bound, anchors, self.query))
        result = preserve_recovery_pair(bound, anchors, anchors[:1], self.query, {})
        self.assertEqual(result[0], anchors[0])
        self.assertEqual({a['file_path'] for a in result}, set(self.protocol['sources']))
        self.assertEqual(preserve_recovery_pair(bound, anchors, anchors, self.query, {}), anchors)

    def test_copies_and_original_query_binding(self):
        bound = self.bound(); anchors = bound['code_anchors']
        for value in [dict(bound), copy.copy(bound), copy.deepcopy(bound), json.loads(json.dumps(bound))]:
            self.assertFalse(valid(value, anchors, self.query))
        self.assertFalse(valid(bound, anchors, 'Locate the registry branch and store sync owners.'))
        changed = copy.deepcopy(anchors); changed[0]['symbol'] = 'Other'
        self.assertFalse(valid(bound, changed, self.query))
        bound._receipts = None
        self.assertFalse(valid(bound, anchors, self.query))

    def test_changed_state_identity_fails_closed(self):
        for key, value in [('qualified_name', 'Other.sessions'), ('source_digest', '0' * 64), ('start_line', 3)]:
            rows = copy.deepcopy(self.rows)
            next(r for r in rows if r['symbol_type'] == 'state')[key] = value
            self.assertIs(self.bound(rows=rows), self.handoff)

    def test_stale_source_and_field_shadow(self):
        path = self.root / 'src/stores/SessionSyncStore.ets'
        path.write_text(path.read_text() + '// changed\n')
        self.assertIs(self.bound(), self.handoff)

    def test_protected_and_range_change(self):
        for key in ('identity_match', 'log_identity_match', 'graph_neighbor', 'graph_relation'):
            handoff = copy.deepcopy(self.handoff); handoff['code_anchors'][0][key] = True
            self.assertIs(self.bound(handoff=handoff), handoff)
        handoff = copy.deepcopy(self.handoff); handoff['code_anchors'][1]['start_line'] += 1
        self.assertIs(self.bound(handoff=handoff), handoff)

    def test_whole_file_drift_after_binding(self):
        bound = self.bound()
        self.assertTrue(current_sources(bound))
        path = self.root / 'src/stores/SessionSyncStore.ets'
        path.write_text(path.read_text() + 'class Shadow {}\n')
        self.assertFalse(current_sources(bound))
        self.assertFalse(accepted_output(bound, self.before['compact'], self.before['compact']))

    def test_no_new_ranges_and_budget_guard(self):
        bound = self.bound()
        old = self.before['compact']
        self.assertFalse(accepted_output(bound, old, old))  # Missing registry is not success.
        candidate = copy.deepcopy(old)
        candidate['output_budget']['estimated_tokens'] = 1501
        self.assertFalse(accepted_output(bound, old, candidate))


if __name__ == '__main__':
    unittest.main()
