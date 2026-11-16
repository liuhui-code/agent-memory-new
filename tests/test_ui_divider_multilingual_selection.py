"""Fresh normal source indexes; no saved outputs or evidence-directory dependencies."""
from copy import copy, deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tests.archive_create_write_test_support import cli, snapshot_database, restore_database
from tools.agent_memory_runtime.storage import resolve_project, connect
from tools.agent_memory_runtime.context_composition import build_context_facade
from tools.agent_memory_runtime.context_compact import compact_context
from tools.agent_memory_runtime.context_record_loop_transaction import restore_whitelist
from tools.agent_memory_runtime.query_ui_divider_selection import (
    DividerContext, bind_divider_context, divider_receipt, compact_divider,
)
from tools.agent_memory_runtime.query_ui_divider_multilingual_request import parse_multilingual_divider_request
from tools.agent_memory_runtime.query_ui_divider_method_scope import method_rooted_frames
from tools.agent_memory_runtime.query_ui_divider_negative import negative_log_conflict, resolve_negative_declarations
from tools.agent_memory_runtime.query_ui_divider_multilingual_selection import qualified_multilingual_divider
from tools.agent_memory_runtime.query_ui_divider_guard import protected_divider
from tools.agent_memory_runtime.query_ui_divider_request import divider_identity_query
from tools.agent_memory_runtime.query_record_loop_selection import protected_record_loop
from tools.agent_memory_runtime.log_event_identity import event_match

P = json.loads((Path(__file__).parent/'fixtures/ui_divider_multilingual.json').read_text())


class MultilingualDividerSelection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(); cls.addClassCleanup(cls.tmp.cleanup)
        cls.projects = {}; cls.saved = {}; cls.samples = {}
        for cohort, sources in P['sources'].items():
            root = Path(cls.tmp.name)/cohort; source = root/'source'; source.mkdir(parents=True)
            for name, body in sources.items():
                f = source/name; f.parent.mkdir(parents=True, exist_ok=True); f.write_text(body)
            project = resolve_project(str(source), str(root/'memory'))
            cli(project, 'init'); cli(project, 'learn-path', '--path', '.', '--json')
            cls.projects[cohort] = project; cls.saved[cohort] = snapshot_database(project)
            cls.addClassCleanup(cls.saved[cohort].close)
            for case in (c for c in P['cases'] if c['cohort'] == cohort):
                restore_database(project, cls.saved[cohort]); captured = []
                def observe(_p, _q, baseline, pool):
                    captured.append((deepcopy(baseline), deepcopy(pool))); return baseline
                with patch('tools.agent_memory_runtime.query_ui_divider_selection.bind_divider_context', side_effect=observe):
                    raw = build_context_facade(project).execute(case['query']); compact = compact_context(raw)
                assert len(captured) == 1
                pre, pool = captured[0]
                cls.samples[case['id']] = (cohort, case['query'], pre, deepcopy(dict(raw)), compact, pool)

    def setUp(self):
        for cohort, project in self.projects.items():
            restore_database(project, self.saved[cohort])
            for name, body in P['sources'][cohort].items():
                (project.root/name).write_text(body)

    def sample(self, case='core-same_file'):
        cohort, query, pre, raw, compact, pool = self.samples[case]
        return self.projects[cohort], query, deepcopy(pre), deepcopy(raw), deepcopy(compact), deepcopy(pool)

    def bind(self, case='core-same_file'):
        project, query, _, raw, compact, pool = self.sample(case)
        return bind_divider_context(project, query, raw, pool), raw, compact

    def full_pool(self, project):
        # Unit-only identity scope. Never claimed as a public retrieval observation.
        with connect(project) as db:
            rows = [dict(r, kind='symbol') for r in db.execute('SELECT * FROM code_symbols')]
            rows += [dict(r, kind='file') for r in db.execute('SELECT * FROM code_files')]
        return rows

    def test_real_glyph_and_account_build_only_roots(self):
        for case, owner in [('core-glyph-map', 'GlyphList'), ('core-account-map', 'AccountCards')]:
            project, query, _, raw, compact, pool = self.sample(case)
            self.assertTrue(pool); self.assertTrue(all(r['kind']=='symbol' and r['symbol']=='build' for r in pool))
            descriptor = parse_multilingual_divider_request(query)
            scope = method_rooted_frames(project, pool, descriptor.qualifiers)
            self.assertIsNotNone(scope)
            self.assertEqual([f['owner']['symbol'] for f in scope[0]], [owner])
            self.assertTrue(scope[3])
            self.assertIsNone(qualified_multilingual_divider(project, descriptor, pool))
            self.assertIs(bind_divider_context(project, query, raw, pool), raw)

    def test_every_frozen_mapping_only_query_keeps_baseline(self):
        observed = 0
        for case in P['cases']:
            descriptor = parse_multilingual_divider_request(case['query'])
            if descriptor is None or descriptor.excluded_names:
                continue
            project, query, _, raw, compact, pool = self.sample(case['id'])
            self.assertIs(bind_divider_context(project, query, raw, pool), raw, case['id'])
            self.assertIsNone(qualified_multilingual_divider(project, descriptor, pool))
            observed += 1
        self.assertGreaterEqual(observed, 4)

    def unit_absent_name_log_sample(self):
        # A unit-only negative-scope argument around a normally captured log.
        # No CLI query is rerun, and frozen fixture query/source bytes stay intact.
        project, query, pre, raw, compact, pool = self.sample('supp-incidental-log-control')
        query = query[:-1] + '，不要返回 GlyphAbsent。'
        pre['query'] = query; raw['query'] = query
        return project, query, pre, raw, compact, pool

    def test_same_file_exclusion_disjoint_and_retained_method_complete(self):
        result, raw, baseline = self.bind(); self.assertIsInstance(result, DividerContext)
        output = compact_divider(result, baseline); anchors = output['query_handoff']['code_anchors']
        self.assertEqual(len(anchors), 1)
        self.assertEqual(anchors[0]['read_window'], {'start_line': 3, 'end_line': 7})
        self.assertEqual(anchors[0]['source_excerpts'][0]['end_line'], 7)
        info = json.loads(result._frames); declaration = info['negative_identities'][0]['declaration']
        self.assertEqual((declaration['start_line'], declaration['end_line']), (10, 16))
        for excerpt in anchors[0]['source_excerpts']:
            self.assertLess(excerpt['end_line'], declaration['start_line'])
            source = P['sources']['core-same_file']['GlyphPanel.ets']
            self.assertEqual(excerpt['content'], '\n'.join(source.splitlines()[2:7]))
        self.assertEqual(restore_whitelist(output, baseline), baseline)
        self.assertLessEqual(output['output_budget']['estimated_tokens'], 1500)
        self.assertIsNone(output['query_handoff']['callable_evidence']['primary'])

    def test_real_noop_model_label_and_absent_keep_both_positives(self):
        for case in ('supp-noop-model', 'supp-noop-label', 'supp-noop-absent'):
            result, raw, compact = self.bind(case)
            self.assertIsInstance(result, DividerContext, case)
            self.assertCountEqual([r['owner_name'] for r in result._members], ['GlyphList', 'GlyphRows'])
            output = compact_divider(result, compact)
            self.assertEqual(restore_whitelist(output, compact), compact)
            self.assertEqual(dict(result), raw)
            self.assertEqual(len(output['query_handoff']['code_anchors']), 2)

    def test_real_negative_class_log_conflict_at_pending_boundary(self):
        project, query, pre, raw, _, pool = self.sample('supp-negative-log')
        logs = pre['query_handoff']['log_anchors']; self.assertEqual(len(logs), 1)
        self.assertEqual((logs[0]['file_path'], logs[0]['line']), ('GlyphLogOwner.ts', 3))
        projected = divider_identity_query(query)
        self.assertTrue(protected_record_loop(pre, query, pool, pending=True))
        self.assertFalse(protected_record_loop(pre, projected, pool, pending=True))
        # This public control did NOT exercise exact-event priority.
        self.assertEqual([event_match(log, query)['priority'] for log in logs], [0])
        qualified = qualified_multilingual_divider(project, parse_multilingual_divider_request(query), pool)
        self.assertIsNotNone(qualified)
        info = json.loads(qualified[3]); declaration = info['negative_identities'][0]['declaration']
        self.assertEqual((declaration['start_line'], declaration['end_line']), (1, 5))
        self.assertTrue(negative_log_conflict(pre, qualified[3]))
        self.assertIs(bind_divider_context(project, query, pre, pool), pre)
        self.assertIs(bind_divider_context(project, query, raw, pool), raw)

    def test_complete_query_is_used_for_event_and_log_owner_helpers(self):
        _, query, pre, _, _, pool = self.sample('supp-negative-log')
        with patch('tools.agent_memory_runtime.query_ui_divider_guard.protected_record_loop', return_value=False), \
             patch('tools.agent_memory_runtime.query_ui_divider_guard.event_match', return_value={'priority': 2}) as match:
            self.assertTrue(protected_divider(pre, query, pool, pending=True))
            match.assert_called_once_with(pre['query_handoff']['log_anchors'][0], query)
        with patch('tools.agent_memory_runtime.query_ui_divider_guard.protected_record_loop', return_value=False), \
             patch('tools.agent_memory_runtime.query_ui_divider_guard.event_match', return_value={'priority': 0}), \
             patch('tools.agent_memory_runtime.query_ui_divider_guard.independently_named_log_owner', return_value=True) as named:
            self.assertTrue(protected_divider(pre, query, pool, pending=True))
            named.assert_called_once_with(pre['query_handoff']['log_anchors'][0], query)

    def test_wrapper_and_call_path_unknowns_reject_without_deleting_logs(self):
        project, query, _, raw, _, pool = self.unit_absent_name_log_sample()
        result = bind_divider_context(project, query, raw, pool)
        self.assertIsInstance(result, DividerContext)
        for key, value in [('wrapper_symbol', 'wrap'), ('wrapper_depth', 1),
                           ('call_path', ['report']), ('call_path_locations', [{'line': 1}])]:
            changed = deepcopy(raw); changed['query_handoff']['log_anchors'][0][key] = value
            self.assertTrue(negative_log_conflict(changed, result._frames), key)
            self.assertIs(bind_divider_context(project, query, changed, pool), changed)
        for line in (None, 0, True, '3'):
            project, query, pre, _, _, pool = self.sample('supp-negative-log')
            result = qualified_multilingual_divider(project, parse_multilingual_divider_request(query), pool)
            pre['query_handoff']['log_anchors'][0]['line'] = line
            self.assertTrue(negative_log_conflict(pre, result[3]))

    def test_missing_original_build_cannot_be_completed_from_database(self):
        project, query, _, raw, _, pool = self.sample('core-glyph-map')
        self.assertIs(bind_divider_context(project, query, raw, []), raw)
        project, query, _, raw, _, pool = self.sample()
        removed = [r for r in pool if not (r.get('kind')=='symbol' and r.get('owner_name')=='GlyphRows')]
        self.assertLess(len(removed), len(pool))
        self.assertIs(bind_divider_context(project, query, raw, removed), raw)

    def test_conflicting_pool_witnesses_are_not_ignored(self):
        project, query, _, raw, _, pool = self.sample('core-glyph-map')
        with connect(project) as db:
            owner = dict(db.execute("SELECT * FROM code_symbols WHERE symbol='GlyphList'").fetchone())
            file = dict(db.execute("SELECT * FROM code_files WHERE file_path='GlyphList.ets'").fetchone())
        for row, kind in [(owner, 'symbol'), (file, 'file')]:
            row = dict(row, kind=kind); row['source_digest'] = 'wrong'
            self.assertIs(bind_divider_context(project, query, raw, pool+[row]), raw)

    def test_missing_parent_and_file_database_rows_fail_closed(self):
        project, query, _, raw, _, pool = self.sample('core-glyph-map')
        with connect(project) as db: db.execute("DELETE FROM code_symbols WHERE symbol='GlyphList'")
        self.assertIs(bind_divider_context(project, query, raw, pool), raw)
        restore_database(project, self.saved['core-glyph'])
        with connect(project) as db: db.execute("DELETE FROM code_files WHERE file_path='GlyphList.ets'")
        self.assertIs(bind_divider_context(project, query, raw, pool), raw)

    def test_duplicate_declaration_and_field_name_are_ambiguous(self):
        for case in ('core-duplicate', 'core-field_collision'):
            result, raw, _ = self.bind(case)
            self.assertIs(result, raw, case)

    def test_stale_source_and_receipt_identity_changes_reject(self):
        result, _, _ = self.bind(); self.assertIsInstance(result, DividerContext)
        project = self.projects['core-same_file']; path = project.root/'GlyphPanel.ets'
        path.write_text(path.read_text()+'\n')
        self.assertIsNone(divider_receipt(result))
        path.write_text(P['sources']['core-same_file']['GlyphPanel.ets'])
        self.assertIsNotNone(divider_receipt(result))
        with connect(project) as db: db.execute("UPDATE code_symbols SET index_generation=index_generation+1 WHERE symbol='GlyphRows'")
        self.assertIsNone(divider_receipt(result))

    def test_query_descriptor_receipt_and_serialization_bindings(self):
        result, _, compact = self.bind(); self.assertIsInstance(result, DividerContext)
        for clone in (dict(result), copy(result), deepcopy(result), json.loads(json.dumps(result))):
            self.assertIsNone(divider_receipt(clone))
        result['query'] = result['query'].replace('GlyphRows', 'GlyphList')
        self.assertIsNone(divider_receipt(result)); self.assertIs(compact_divider(result, compact), compact)
        result, _, _ = self.bind(); info = json.loads(result._frames)
        info['descriptor']['qualifiers'] = ['account']; result._frames = json.dumps(info)
        self.assertIsNone(divider_receipt(result))

    def test_uniform_union_limit_before_exclusion_unit_scope(self):
        project, query, _, raw, _, _ = self.sample('core-union_thirteen')
        pool = self.full_pool(project); descriptor = parse_multilingual_divider_request(query)
        self.assertIsNone(method_rooted_frames(project, pool, descriptor.qualifiers))
        self.assertIs(bind_divider_context(project, query, raw, pool), raw)

    def test_complete_set_anchor_cap_and_budget_unit_scope(self):
        project, query, _, raw, compact, _ = self.sample('core-four_after_exclusion')
        bound = bind_divider_context(project, query, raw, self.full_pool(project))
        self.assertIsInstance(bound, DividerContext)
        self.assertEqual(len(bound._anchors), 4)
        self.assertIs(compact_divider(bound, compact), compact)
        bound, _, compact = self.bind()
        huge = deepcopy(compact); huge['query_handoff']['unchanged_note'] = 'x'*10000
        self.assertIs(compact_divider(bound, huge), huge)


    def test_method_only_unrelated_member_cannot_hide_samefile_matching_component(self):
        # Unit scope from normal metadata: extra file enters solely through ping,
        # never through its matching component/build/file rows.
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary)/'source'; source.mkdir()
            base = P['sources']['core-glyph']['GlyphList.ets']
            mixed = ('export class ExtraProbe {\n ping(): number { return 1 }\n}\n'
                     + base.replace('GlyphList', 'GlyphHidden'))
            (source/'GlyphList.ets').write_text(base)
            (source/'ExtraMixed.ets').write_text(mixed)
            project = resolve_project(str(source), str(Path(temporary)/'memory'))
            cli(project, 'init'); cli(project, 'learn-path', '--path', '.', '--json')
            with connect(project) as db:
                root = dict(db.execute("SELECT * FROM code_symbols WHERE owner_name='GlyphList' AND symbol='build'").fetchone())
                unrelated = dict(db.execute("SELECT * FROM code_symbols WHERE owner_name='ExtraProbe' AND symbol='ping'").fetchone())
                hidden = dict(db.execute("SELECT * FROM code_symbols WHERE owner_name='GlyphHidden' AND symbol='build'").fetchone())
                declaration = dict(db.execute("SELECT * FROM code_symbols WHERE symbol='GlyphHidden'").fetchone())
            self.assertEqual(hidden['source_digest'], unrelated['source_digest'])
            self.assertEqual(declaration['file_path'], 'ExtraMixed.ets')
            pool = [dict(root, kind='symbol'), dict(unrelated, kind='symbol')]
            self.assertTrue(all(r['id'] != hidden['id'] for r in pool))
            self.assertIsNotNone(method_rooted_frames(project, pool[:1], ('glyph',)))
            self.assertIsNone(method_rooted_frames(project, pool, ('glyph',)))
            descriptor = parse_multilingual_divider_request('字形列表分隔线粗细错误，请定位 divider 的源码。')
            self.assertIsNone(qualified_multilingual_divider(project, descriptor, pool))

    def test_negative_metadata_same_digest_wrong_bounds_reject(self):
        project, query, _, raw, _, pool = self.sample('supp-noop-model')
        self.assertIsNotNone(resolve_negative_declarations(project, ('GlyphModel',)))
        for field, value in [('start_line', 2), ('end_line', 2)]:
            with self.subTest(field=field):
                restore_database(project, self.saved['supp-noop'])
                with connect(project) as db:
                    digest = db.execute("SELECT source_digest FROM code_symbols WHERE symbol='GlyphModel'").fetchone()[0]
                    db.execute('UPDATE code_symbols SET '+field+"=? WHERE symbol='GlyphModel'", (value,))
                    self.assertEqual(db.execute("SELECT source_digest FROM code_symbols WHERE symbol='GlyphModel'").fetchone()[0], digest)
                self.assertIsNone(resolve_negative_declarations(project, ('GlyphModel',)))
                self.assertIs(bind_divider_context(project, query, raw, pool), raw)

    def test_negative_class_role_and_parent_metadata_remain_validated(self):
        project, _, _, _, _, _ = self.sample('supp-noop-model')
        with connect(project) as db:
            original = dict(db.execute("SELECT * FROM code_symbols WHERE symbol='GlyphModel'").fetchone())
        self.assertEqual(original['symbol_type'], 'class')
        self.assertEqual(original['owner_kind'], 'model')
        self.assertIsNotNone(resolve_negative_declarations(project, ('GlyphModel',)))
        for field, value in [('owner_kind', 'component'), ('owner_kind', 'unknown'),
                             ('owner_kind', None), ('owner_name', 'Other')]:
            restore_database(project, self.saved['supp-noop'])
            with connect(project) as db:
                db.execute('UPDATE code_symbols SET '+field+"=? WHERE symbol='GlyphModel'", (value,))
            self.assertIsNone(resolve_negative_declarations(project, ('GlyphModel',)), (field, value))

    def test_negative_metadata_same_digest_forged_name_reject(self):
        project, query, _, raw, _, pool = self.sample('supp-noop-model')
        with connect(project) as db:
            old = dict(db.execute("SELECT * FROM code_symbols WHERE symbol='GlyphModel'").fetchone())
            db.execute("UPDATE code_symbols SET symbol='GlyphRenamed',qualified_name='GlyphRenamed' WHERE id=?", (old['id'],))
            row = dict(db.execute('SELECT * FROM code_symbols WHERE id=?', (old['id'],)).fetchone())
            self.assertEqual(row['source_digest'], old['source_digest'])
        self.assertIsNone(resolve_negative_declarations(project, ('GlyphRenamed',)))
        changed_query = query.replace('GlyphModel', 'GlyphRenamed')
        changed = deepcopy(raw); changed['query'] = changed_query
        self.assertIs(bind_divider_context(project, changed_query, changed, pool), changed)

    def test_wrapped_class_effect_or_unknown_log_shape_reject_with_empty_paths(self):
        project, query, _, raw, _, pool = self.unit_absent_name_log_sample()
        result = bind_divider_context(project, query, raw, pool)
        self.assertIsInstance(result, DividerContext)
        original = raw['query_handoff']['log_anchors'][0]
        self.assertFalse(original.get('wrapper_symbol'))
        self.assertFalse(original.get('call_path'))
        for key, value in [('evidence_class', 'static_wrapped'), ('evidence_class', None),
                           ('evidence_class', 'unknown'), ('effect_id', 1), ('effect_id', 0),
                           ('file_path', None), ('file_path', ''), ('line', None),
                           ('line', False), ('line', '3'), ('line', -1)]:
            changed = deepcopy(raw); changed['query_handoff']['log_anchors'][0][key] = value
            self.assertTrue(negative_log_conflict(changed, result._frames), (key, value))
            self.assertIs(bind_divider_context(project, query, changed, pool), changed)
        for logs in (None, {}, [None], ['log']):
            changed = deepcopy(raw); changed['query_handoff']['log_anchors'] = logs
            self.assertTrue(negative_log_conflict(changed, result._frames))
            self.assertIs(bind_divider_context(project, query, changed, pool), changed)

    def test_all_positives_excluded_is_complete_fallback(self):
        project, query, _, raw, _, pool = self.sample()
        query = query.replace('GlyphRows', 'GlyphList 或 GlyphRows')
        raw['query'] = query
        self.assertIsNone(qualified_multilingual_divider(project, parse_multilingual_divider_request(query), pool))
        self.assertIs(bind_divider_context(project, query, raw, pool), raw)

    def test_crossproject_root_and_negative_file_drift_reject(self):
        project, query, _, raw, _, pool = self.sample('core-glyph-map')
        pool[0]['project_id'] = 'different-project'
        self.assertIs(bind_divider_context(project, query, raw, pool), raw)
        project, query, _, raw, _, pool = self.sample('supp-noop-model')
        bound = bind_divider_context(project, query, raw, pool)
        self.assertIsInstance(bound, DividerContext)
        self.assertIn('GlyphModel.ts', [path for path, _ in bound._files])
        source = project.root/'GlyphModel.ts'
        source.write_text(source.read_text().replace('""', '"changed"'))
        self.assertIsNone(divider_receipt(bound))
        source.write_text(P['sources']['supp-noop']['GlyphModel.ts'])
        self.assertIsNotNone(divider_receipt(bound))
        with connect(project) as db:
            db.execute("UPDATE code_symbols SET index_generation=index_generation+1 WHERE symbol='GlyphModel'")
        self.assertIsNone(divider_receipt(bound))


if __name__ == '__main__': unittest.main()
