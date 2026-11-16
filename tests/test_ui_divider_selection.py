from copy import copy, deepcopy
import json, tempfile, unittest
from unittest.mock import patch
from tests.command_table_test_support import prepare
from tools.agent_memory_runtime.context_composition import build_context_facade
from tools.agent_memory_runtime.context_compact import compact_context
from tools.agent_memory_runtime.context_record_loop_transaction import restore_whitelist
from tools.agent_memory_runtime.query_ui_divider_request import divider_request, qualifier_matches
from tools.agent_memory_runtime.query_ui_divider_selection import (DividerContext, bind_divider_context, divider_receipt, compact_divider, enrich_divider)
from tools.agent_memory_runtime.storage import connect

Q = 'Locate the ArkTS glyph divider stroke width implementation.'
SOURCE = '''@Component
export struct GlyphList {
 build() {
  List() {
   ListItem() { Text('glyph') }
  }.divider({ strokeWidth: 2 })
 }
}
'''
ABILITY = '''export class EntryAbility {
 onWindowStageCreate(stage: WindowStage): void {
  stage.loadContent('pages/Entry')
 }
 onWindowStageDestroy(): void {
  this.stage.release()
 }
}
'''
SOURCES = {'GlyphList.ets': SOURCE, 'EntryAbility.ets': ABILITY}


def ordinary(project, query=Q):
    pools = []
    def capture(_p, _q, baseline, pool):
        pools.append(deepcopy(pool)); return baseline
    with patch('tools.agent_memory_runtime.query_ui_divider_selection.bind_divider_context', side_effect=capture):
        raw = build_context_facade(project).execute(query); compact = compact_context(raw)
    assert len(pools) == 1
    return deepcopy(dict(raw)), compact, pools[0]


class DividerRequest(unittest.TestCase):
    def test_complete_role_and_opaque_qualifier(self):
        self.assertEqual(divider_request(Q), 'glyph')
        self.assertEqual(divider_request('Find the inventory divider stroke width implementation'), 'inventory')
        for query in [Q+' and logs', Q.replace('glyph', 'GlyphList'), Q.replace('glyph', 'not'),
                      'Find the ArkTS application startup implementation.', 'Find the literal "divider".',
                      'Find the glyph divider API implementation.', 'Do not '+Q, Q.replace('glyph', 'both')]:
            self.assertIsNone(divider_request(query), query)
        self.assertTrue(qualifier_matches('glyph', 'GlyphList'))
        self.assertFalse(qualifier_matches('glyph', 'HieroglyphList'))
        self.assertFalse(qualifier_matches('glyph', 'GlyphList.ets'))


class DividerSelection(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.project = prepare(self.tmp.name, sources=SOURCES)
        self.base, self.compact, self.pool = ordinary(self.project)
    def tearDown(self): self.tmp.cleanup()
    def bind(self, pool=None, base=None):
        return bind_divider_context(self.project, Q, self.base if base is None else base,
                                    self.pool if pool is None else pool)
    def test_public_identity_and_complete_method(self):
        bound = self.bind(); self.assertIsInstance(bound, DividerContext)
        out = compact_divider(bound, self.compact)
        self.assertIsNot(out, self.compact); self.assertEqual(restore_whitelist(out, self.compact), self.compact)
        self.assertEqual(dict(bound), self.base)
        anchors = out['query_handoff']['code_anchors']; self.assertEqual(len(anchors), 1)
        a = anchors[0]; self.assertEqual((a['symbol'], a['symbol_type']), ('build', 'function'))
        self.assertEqual(a['source_excerpts'][0]['content'], '\n'.join(SOURCE.splitlines()[2:7]))
        self.assertEqual(out['query_handoff']['callable_evidence']['certainty'], 'uncertain')
        self.assertIsNone(out['query_handoff']['callable_evidence']['primary'])
        self.assertLessEqual(out['output_budget']['estimated_tokens'], 1500)
    def test_each_original_member_required(self):
        for kind, symbol in [('file', 'GlyphList'), ('symbol', 'GlyphList'), ('symbol', 'build')]:
            pool = [r for r in self.pool if not (r.get('file_path') == 'GlyphList.ets'
                    and r['kind'] == kind and r.get('symbol') == symbol)]
            self.assertLess(len(pool), len(self.pool)); self.assertIs(self.bind(pool), self.base)
    def test_type_value_alias_signature_and_owner_corruption(self):
        for field, value in [('id', True), ('index_generation', True), ('symbol_key', None),
                             ('signature', 'ordinary'), ('qualified_name', 'Other.build'), ('owner_name', 'Other')]:
            pool = deepcopy(self.pool)
            row = next(r for r in pool if r['kind'] == 'symbol' and r.get('symbol') == 'build')
            row[field] = value
            self.assertIs(self.bind(pool), self.base, field)
        pool = deepcopy(self.pool); row = next(r for r in pool if r['kind'] == 'symbol' and r.get('symbol') == 'build')
        row['signature'] = 'ordinary'; row['qualified_name'] = 'ordinary'
        self.assertIs(self.bind(pool), self.base)
    def test_receipt_copy_source_and_db_changes(self):
        r = self.bind(); self.assertIsInstance(r, DividerContext)
        for copied in [dict(r), copy(r), deepcopy(r), json.loads(json.dumps(r))]:
            self.assertIsNone(divider_receipt(copied))
        with connect(self.project) as db:
            db.execute("UPDATE code_symbols SET signature='changed' WHERE symbol='build'")
        self.assertIsNone(divider_receipt(r))
        with connect(self.project) as db:
            db.execute("UPDATE code_symbols SET signature='build():unknown' WHERE symbol='build'")
        self.assertIsNotNone(divider_receipt(r))
        (self.project.root/'GlyphList.ets').write_text(SOURCE+'\n')
        self.assertIsNone(divider_receipt(r)); self.assertIs(self.bind(), self.base)
    def test_protected_fields_budget_and_snapshot(self):
        for flag in ['identity_match', 'log_identity_match', 'graph_neighbor', 'graph_relation']:
            base = deepcopy(self.base); base['query_handoff']['code_anchors'][0][flag] = True
            self.assertIs(self.bind(base=base), base)
        r = self.bind(); huge = deepcopy(self.compact); huge['query_handoff']['unknown'] = 'x'*8000
        self.assertIs(compact_divider(r, huge), huge)
        r._anchors[0]['record_ids'][0] += 1; self.assertIsNone(divider_receipt(r))
        r = self.bind(); path = deepcopy(self.base['query_handoff']['path_context']); path['activated'] = True
        self.assertNotIsInstance(enrich_divider(r, Q, path, self.base['source_freshness']), DividerContext)
    def test_two_same_file_positive_methods_and_missing_one(self):
        with tempfile.TemporaryDirectory() as t:
            project = prepare(t, sources={'GlyphList.ets': SOURCE+'\n'+SOURCE.replace('GlyphList', 'GlyphRows'), 'EntryAbility.ets': ABILITY})
            base, compact, pool = ordinary(project); r = bind_divider_context(project, Q, base, pool)
            self.assertIsInstance(r, DividerContext)
            out = compact_divider(r, compact); self.assertEqual(len(out['query_handoff']['code_anchors']), 2)
            removed = [x for x in pool if not (x.get('owner_name') == 'GlyphRows' and x.get('symbol') == 'build')]
            self.assertLess(len(removed), len(pool)); self.assertIs(bind_divider_context(project, Q, base, removed), base)
    def test_nonmatch_source_digest_remains_bound(self):
        with tempfile.TemporaryDirectory() as t:
            other = '''@Component
export struct GlyphPanel {
 build() { Grid() { TextInput({ placeholder: 'label' }) }.shadow({ radius: 2 }) }
}
'''
            project = prepare(t, sources={**SOURCES, 'GlyphPanel.ets': other})
            base, compact, pool = ordinary(project); r = bind_divider_context(project, Q, base, pool)
            self.assertIsInstance(r, DividerContext)
            self.assertIn('GlyphPanel.ets', [p for p, _ in r._files])
            (project.root/'GlyphPanel.ets').write_text(other.replace('Grid', 'List'))
            self.assertIsNone(divider_receipt(r))
    def test_source_only_matching_declaration_cannot_hide_outside_db_frames(self):
        with tempfile.TemporaryDirectory() as t:
            project = prepare(t, sources={'GlyphList.ets': SOURCE+'\n'+SOURCE.replace('GlyphList', 'GlyphRows'), 'EntryAbility.ets': ABILITY})
            base, compact, pool = ordinary(project)
            with connect(project) as db:
                db.execute("DELETE FROM code_symbols WHERE symbol='GlyphRows' OR owner_name='GlyphRows'")
            pool = [r for r in pool if r.get('symbol') != 'GlyphRows' and r.get('owner_name') != 'GlyphRows']
            self.assertIs(bind_divider_context(project, Q, base, pool), base)
    def test_nonempty_key_alias_across_pool_paths_is_rejected(self):
        with connect(self.project) as db:
            row = dict(db.execute("SELECT * FROM code_symbols WHERE symbol='build'").fetchone())
            row.pop('id'); row['file_path'] = 'UnrecalledAlias.ets'
            row['qualified_name'] = 'UnrecalledAlias.build'; row['owner_name'] = 'UnrecalledAlias'
            db.execute('INSERT INTO code_symbols ('+','.join(row)+') VALUES ('+','.join('?' for _ in row)+')', list(row.values()))
        self.assertIs(self.bind(), self.base)
    def test_consistent_same_pool_key_conflict_and_null_positive_key(self):
        build = next(r for r in self.pool if r['kind'] == 'symbol' and r.get('symbol') == 'build')
        other = next(r for r in self.pool if r['kind'] == 'symbol' and r.get('symbol') == 'EntryAbility')
        pool = deepcopy(self.pool)
        next(r for r in pool if r['kind'] == 'symbol' and r['id'] == other['id'])['symbol_key'] = build['symbol_key']
        with connect(self.project) as db:
            db.execute('UPDATE code_symbols SET symbol_key=? WHERE id=?', (build['symbol_key'], other['id']))
        self.assertIs(self.bind(pool), self.base)
        with connect(self.project) as db:
            db.execute('UPDATE code_symbols SET symbol_key=? WHERE id=?', (other['symbol_key'], other['id']))
            db.execute('UPDATE code_symbols SET symbol_key=NULL WHERE id=?', (build['id'],))
        pool = deepcopy(self.pool)
        next(r for r in pool if r['kind'] == 'symbol' and r['id'] == build['id'])['symbol_key'] = None
        self.assertIs(self.bind(pool), self.base)
    def test_empty_keys_on_ordinary_symbols_are_not_aliases(self):
        ordinary_row = next(r for r in self.pool if r['kind'] == 'symbol' and r.get('symbol') == 'EntryAbility')
        for key in (None, ''):
            with self.subTest(key=key):
                pool = deepcopy(self.pool)
                target = next(r for r in pool if r['kind'] == 'symbol' and r['id'] == ordinary_row['id'])
                target['symbol_key'] = key
                with connect(self.project) as db:
                    db.execute('UPDATE code_symbols SET symbol_key=? WHERE id=?', (key, ordinary_row['id']))
                    row = dict(db.execute('SELECT * FROM code_symbols WHERE id=?', (ordinary_row['id'],)).fetchone())
                    row.pop('id'); row['file_path'] = 'UnrecalledNull.ets'
                    row['symbol'] = 'UnrecalledNull'; row['qualified_name'] = 'UnrecalledNull'
                    inserted = db.execute('INSERT INTO code_symbols ('+','.join(row)+') VALUES ('+','.join('?' for _ in row)+')', list(row.values())).lastrowid
                self.assertIsInstance(self.bind(pool), DividerContext)
                with connect(self.project) as db:
                    db.execute('DELETE FROM code_symbols WHERE id=?', (inserted,))
                    db.execute('UPDATE code_symbols SET symbol_key=? WHERE id=?', (ordinary_row['symbol_key'], ordinary_row['id']))
    def test_facade_and_direct_account_once(self):
        from tools.agent_memory_runtime.query_results import limited_context
        for public in [True, False]:
            with patch('tools.agent_memory_runtime.query_results.record_context_use') as use, patch('tools.agent_memory_runtime.query_results.record_query_miss_if_empty') as miss:
                result = build_context_facade(self.project).execute(Q) if public else limited_context(self.project, Q)
            self.assertIsInstance(result, DividerContext); use.assert_called_once(); miss.assert_called_once()
            self.assertEqual(dict(result)['query_handoff']['code_anchors'], self.base['query_handoff']['code_anchors'])
            if public:
                self.assertEqual(compact_context(result)['query_handoff']['code_anchors'][0]['symbol'], 'build')
            else:
                self.assertIsNone(result['query_handoff'].get('path_context'))
                self.assertEqual(compact_context(result)['query_handoff']['code_anchors'][0]['symbol'], 'EntryAbility')

if __name__ == '__main__': unittest.main()
