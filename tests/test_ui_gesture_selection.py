from copy import copy, deepcopy
import json, tempfile, unittest
from unittest.mock import patch
from tests.command_table_test_support import prepare
from tools.agent_memory_runtime.context_composition import build_context_facade
from tools.agent_memory_runtime.context_compact import compact_context
from tools.agent_memory_runtime.context_record_loop_transaction import restore_whitelist
from tools.agent_memory_runtime.query_ui_gesture_request import gesture_request, qualifier_matches
from tools.agent_memory_runtime.query_ui_gesture_selection import (GestureContext, bind_gesture_context,
    gesture_receipt, compact_gesture, enrich_gesture)
from tools.agent_memory_runtime.storage import connect

Q = 'Locate the tile gesture interaction source.'
SOURCE = '''@Component
export struct TilePanSurface {
  @State dragOffset: number = 0
  build() {
    Stack() {}
      .gesture(
        PanGesture().onActionUpdate((sample: GestureEvent) => {
          this.dragOffset = sample.offsetX
        })
      )
  }
}
'''
HELP = '''@Component
export struct TileGestureHelp {
  build() { Column() { Text('Tile gesture interaction') } }
}
'''
INTERFACE = 'export interface TileState {\n count: number\n pieces: number[]\n}\n'
SOURCES = {'TilePanSurface.ets': SOURCE, 'TileGestureHelp.ets': HELP,
           'ReaderPanSurface.ets': SOURCE.replace('TilePanSurface', 'ReaderPanSurface'),
           'TileState.ets': INTERFACE}


def ordinary(project, query=Q):
    pools = []
    def capture(_p, _q, baseline, pool):
        pools.append(deepcopy(pool)); return baseline
    with patch('tools.agent_memory_runtime.query_ui_gesture_selection.bind_gesture_context', side_effect=capture):
        raw = build_context_facade(project).execute(query); compact = compact_context(raw)
    assert len(pools) == 1
    return deepcopy(dict(raw)), compact, pools[0]


class GestureRequest(unittest.TestCase):
    def test_whole_subject_request(self):
        self.assertEqual(gesture_request(Q), 'tile')
        self.assertEqual(gesture_request('Dragging the tile moves pieces but count and progress remain unchanged. Locate the gesture interaction owner.'), 'tile')
        for query in [Q+' Also logs.', Q.replace('tile', 'TilePanSurface'), Q.replace('tile', 'not'),
                      Q.replace('tile', 'tile and reader'), 'Do not '+Q, "Find literal 'gesture'.",
                      'Dragging the tile moves pieces but count and count remain unchanged. Locate the gesture interaction owner.']:
            self.assertIsNone(gesture_request(query), query)
        self.assertTrue(qualifier_matches('tile', 'TilePanSurface'))
        self.assertFalse(qualifier_matches('tile', 'ReptilePane'))
        self.assertFalse(qualifier_matches('tile', 'Tile.ets'))


class GestureSelection(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.project = prepare(self.tmp.name, sources=SOURCES)
        self.base, self.compact, self.pool = ordinary(self.project)
    def tearDown(self): self.tmp.cleanup()
    def bind(self, pool=None, base=None):
        return bind_gesture_context(self.project, Q, self.base if base is None else base,
                                    self.pool if pool is None else pool)
    def test_real_build_and_noncode(self):
        bound = self.bind(); self.assertIsInstance(bound, GestureContext)
        out = compact_gesture(bound, self.compact)
        self.assertIsNot(out, self.compact); self.assertEqual(restore_whitelist(out, self.compact), self.compact)
        self.assertEqual(dict(bound), self.base)
        anchors = out['query_handoff']['code_anchors']; self.assertEqual(len(anchors), 1)
        a = anchors[0]; self.assertEqual((a['symbol'], a['symbol_type']), ('build', 'function'))
        self.assertEqual(a['source_excerpts'][0]['content'], '\n'.join(SOURCE.splitlines()[3:11]))
        self.assertIn('non_exhaustive', out['query_handoff']['callable_evidence']['boundary'])
        self.assertIsNone(out['query_handoff']['callable_evidence']['primary'])
        self.assertLessEqual(out['output_budget']['estimated_tokens'], 1500)
    def test_all_original_positive_members_required(self):
        for kind, symbol in [('file', 'TilePanSurface'), ('symbol', 'TilePanSurface'), ('symbol', 'build'), ('symbol', 'onActionUpdate')]:
            pool = [r for r in self.pool if not (r.get('file_path') == 'TilePanSurface.ets'
                    and r['kind'] == kind and r.get('symbol') == symbol)]
            self.assertLess(len(pool), len(self.pool)); self.assertIs(self.bind(pool), self.base)
    def test_type_identity_and_callback_corruption(self):
        for field, value in [('id', True), ('index_generation', True), ('symbol_key', None),
                             ('signature', 'ordinary'), ('qualified_name', 'Other.onActionUpdate@7'),
                             ('owner_name', 'Other'), ('start_line', 5), ('end_line', 10)]:
            pool = deepcopy(self.pool)
            row = next(r for r in pool if r['kind'] == 'symbol' and r.get('file_path') == 'TilePanSurface.ets' and r.get('symbol') == 'onActionUpdate')
            row[field] = value
            self.assertIs(self.bind(pool), self.base, field)
        pool = deepcopy(self.pool); row = next(r for r in pool if r['kind'] == 'symbol' and r.get('symbol') == 'onActionUpdate')
        row['signature'] = 'ordinary'; row['qualified_name'] = 'ordinary'
        self.assertIs(self.bind(pool), self.base)
    def test_copy_receipt_and_source_db_drift(self):
        bound = self.bind(); self.assertIsInstance(bound, GestureContext)
        for cloned in [dict(bound), copy(bound), deepcopy(bound), json.loads(json.dumps(bound))]:
            self.assertIsNone(gesture_receipt(cloned))
        with connect(self.project) as db:
            db.execute("UPDATE code_symbols SET signature='changed' WHERE symbol='onActionUpdate'")
        self.assertIsNone(gesture_receipt(bound))
        (self.project.root/'TilePanSurface.ets').write_text(SOURCE+'\n')
        self.assertIs(self.bind(), self.base)
    def test_matched_request_log_graph_path_and_identity_guards(self):
        for flag in ['identity_match', 'log_identity_match', 'graph_neighbor', 'graph_relation']:
            base = deepcopy(self.base); base['query_handoff']['code_anchors'][0][flag] = True
            self.assertIs(self.bind(base=base), base)
            base = deepcopy(self.base); base['query_handoff']['log_anchors'] = [dict(message_template='actual trace', **{flag: True})]
            self.assertIs(self.bind(base=base), base)
        base = deepcopy(self.base); base['query_handoff']['path_context']['activated'] = True
        self.assertIs(self.bind(base=base), base)
        pool = deepcopy(self.pool); pool[0]['graph_relation'] = 'calls'
        self.assertIs(self.bind(pool), self.base)
        # Literal event identity on a grammar-matched request still invokes shared guard.
        base = deepcopy(self.base); base['query_handoff']['log_anchors'] = [dict(message_template=Q, logger='console', function='trace', file_path='Trace.ets')]
        self.assertIs(self.bind(base=base), base)
    def test_budget_and_receipt_mutation(self):
        bound = self.bind(); self.assertIsInstance(bound, GestureContext)
        huge = deepcopy(self.compact); huge['query_handoff']['unknown'] = 'x'*8000
        self.assertIs(compact_gesture(bound, huge), huge)
        tiny = deepcopy(self.compact); tiny['output_budget']['target_tokens'] = 1
        self.assertIs(compact_gesture(bound, tiny), tiny)
        bound._anchors[0]['record_ids'][0] += 1; self.assertIsNone(gesture_receipt(bound))
        bound = self.bind(); self.assertNotIsInstance(enrich_gesture(bound, Q+'!', self.base['query_handoff']['path_context'], self.base['source_freshness']), GestureContext)
    def test_nonmatch_source_drift_revokes(self):
        bound = self.bind(); self.assertIsInstance(bound, GestureContext)
        self.assertIn('TileGestureHelp.ets', [p for p, _ in bound._files])
        self.assertIn('TileState.ets', [p for p, _ in bound._files])
        (self.project.root/'TileGestureHelp.ets').write_text(HELP.replace('Column', 'Stack'))
        self.assertIsNone(gesture_receipt(bound))
    def test_alias_across_unrecalled_paths(self):
        with connect(self.project) as db:
            row = dict(db.execute("SELECT * FROM code_symbols WHERE symbol='onActionUpdate' LIMIT 1").fetchone())
            row.pop('id'); row['file_path'] = 'UnrecalledAlias.ets'
            db.execute('INSERT INTO code_symbols ('+','.join(row)+') VALUES ('+','.join('?' for _ in row)+')', list(row.values()))
        self.assertIs(self.bind(), self.base)
    def test_two_same_file_all_callback_members_atomic(self):
        with tempfile.TemporaryDirectory() as t:
            source = SOURCE+'\n'+SOURCE.replace('TilePanSurface', 'TileOtherSurface')
            project = prepare(t, sources={'TilePanSurface.ets': source, 'TileGestureHelp.ets': HELP})
            base, compact, pool = ordinary(project); bound = bind_gesture_context(project, Q, base, pool)
            self.assertIsInstance(bound, GestureContext)
            self.assertEqual(len(compact_gesture(bound, compact)['query_handoff']['code_anchors']), 2)
            removed = [r for r in pool if not (r.get('owner_name') == 'TileOtherSurface' and r.get('symbol') == 'onActionUpdate')]
            self.assertLess(len(removed), len(pool)); self.assertIs(bind_gesture_context(project, Q, base, removed), base)
            (project.root/'TilePanSurface.ets').write_text(source+'\n')
            self.assertIsNone(gesture_receipt(bound))
    def test_source_only_matching_declaration_not_hidden(self):
        with tempfile.TemporaryDirectory() as t:
            project = prepare(t, sources={'TilePanSurface.ets': SOURCE+'\n'+SOURCE.replace('TilePanSurface', 'TileHiddenSurface'), 'TileGestureHelp.ets': HELP})
            base, compact, pool = ordinary(project)
            with connect(project) as db:
                db.execute("DELETE FROM code_symbols WHERE symbol='TileHiddenSurface' OR owner_name='TileHiddenSurface'")
            pool = [r for r in pool if r.get('symbol') != 'TileHiddenSurface' and r.get('owner_name') != 'TileHiddenSurface']
            self.assertIs(bind_gesture_context(project, Q, base, pool), base)
    def test_facade_and_direct_single_accounting(self):
        from tools.agent_memory_runtime.query_results import limited_context
        for public in (True, False):
            with patch('tools.agent_memory_runtime.query_results.record_context_use') as use, patch('tools.agent_memory_runtime.query_results.record_query_miss_if_empty') as miss:
                result = build_context_facade(self.project).execute(Q) if public else limited_context(self.project, Q)
            self.assertIsInstance(result, GestureContext); use.assert_called_once(); miss.assert_called_once()
            self.assertEqual(dict(result)['query_handoff']['code_anchors'], self.base['query_handoff']['code_anchors'])
            if public:
                self.assertEqual(compact_context(result)['query_handoff']['code_anchors'][0]['file_path'], 'TilePanSurface.ets')
            else:
                self.assertIsNone(result['query_handoff'].get('path_context'))
                self.assertEqual(compact_context(result)['query_handoff']['code_anchors'], compact_context(dict(result))['query_handoff']['code_anchors'])

if __name__ == '__main__': unittest.main()
