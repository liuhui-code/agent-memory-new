from copy import deepcopy
import tempfile, unittest
from tests.command_table_test_support import prepare
from tests.test_ui_gesture_selection import SOURCE, HELP, Q, SOURCES, ordinary
from tools.agent_memory_runtime.query_ui_gesture_scope import gesture_frames
from tools.agent_memory_runtime.query_ui_gesture_selection import GestureContext, bind_gesture_context, compact_gesture, gesture_receipt
from tools.agent_memory_runtime.storage import connect


def full_pool(project):
    with connect(project) as db:
        return ([dict(r, kind='file') for r in db.execute('SELECT * FROM code_files')]
                + [dict(r, kind='symbol') for r in db.execute('SELECT * FROM code_symbols')])


class GestureScope(unittest.TestCase):
    def test_frame_bound_is_metadata_set_not_ranking(self):
        sources = {'TileSurface'+str(i)+'.ets': SOURCE.replace('TilePanSurface', 'TileSurface'+str(i)) for i in range(13)}
        with tempfile.TemporaryDirectory() as t:
            project = prepare(t, sources=sources); pool = full_pool(project)
            self.assertIsNone(gesture_frames(project, pool, 'tile'))
            reduced = [r for r in pool if r['file_path'] != 'TileSurface12.ets']
            self.assertEqual(len(gesture_frames(project, reduced, 'tile')), 12)
            self.assertEqual(gesture_frames(project, reduced, 'tile'), gesture_frames(project, list(reversed(reduced)), 'tile'))
    def test_four_positive_methods_fallback_atomically(self):
        sources = {'TileSurface'+str(i)+'.ets': SOURCE.replace('TilePanSurface', 'TileSurface'+str(i)) for i in range(4)}
        with tempfile.TemporaryDirectory() as t:
            project = prepare(t, sources=sources); base, compact, _ = ordinary(project)
            bound = bind_gesture_context(project, Q, base, full_pool(project))
            self.assertIsInstance(bound, GestureContext)
            self.assertIs(compact_gesture(bound, compact), compact)
    def test_unknown_same_domain_class_or_component_not_hidden(self):
        unknowns = ["export class TileCustom {\n install() { this.surface.gesture(this.handler) }\n}\n",
                    SOURCE.replace('TilePanSurface', 'TileCustom').replace('Stack() {}', 'Row() {}')]
        for unknown in unknowns:
            with self.subTest(unknown=unknown), tempfile.TemporaryDirectory() as t:
                project = prepare(t, sources={**SOURCES, 'TileCustom.ets': unknown})
                base, compact, pool = ordinary(project)
                self.assertIs(bind_gesture_context(project, Q, base, full_pool(project)), base)
    def test_callback_null_key_and_same_line_ambiguity(self):
        with tempfile.TemporaryDirectory() as t:
            project = prepare(t, sources=SOURCES); base, compact, pool = ordinary(project)
            target = next(r for r in pool if r['kind'] == 'symbol' and r['file_path'] == 'TilePanSurface.ets' and r.get('symbol') == 'onActionUpdate')
            with connect(project) as db:
                db.execute('UPDATE code_symbols SET symbol_key=NULL WHERE id=?', (target['id'],))
            target['symbol_key'] = None
            self.assertIs(bind_gesture_context(project, Q, base, pool), base)
        chain = 'Stack() {}.gesture(PanGesture().onActionUpdate((sample: GestureEvent) => { this.dragOffset = sample.offsetX }))'
        source = '@Component\nexport struct TilePanSurface {\n @State dragOffset: number = 0\n build() { '+chain+'; '+chain+' }\n}\n'
        with tempfile.TemporaryDirectory() as t:
            project = prepare(t, sources={'TilePanSurface.ets': source, 'TileGestureHelp.ets': HELP})
            base, compact, pool = ordinary(project)
            self.assertIs(bind_gesture_context(project, Q, base, full_pool(project)), base)
    def test_nonqualified_null_keys_do_not_alias(self):
        with tempfile.TemporaryDirectory() as t:
            project = prepare(t, sources=SOURCES); base, compact, pool = ordinary(project)
            target = next(r for r in pool if r['kind'] == 'symbol' and r['file_path'] == 'ReaderPanSurface.ets')
            with connect(project) as db:
                db.execute('UPDATE code_symbols SET symbol_key=NULL WHERE id=?', (target['id'],))
                other = dict(db.execute('SELECT * FROM code_symbols WHERE id=?', (target['id'],)).fetchone())
                other.pop('id'); other['file_path'] = 'UnrecalledNull.ets'
                db.execute('INSERT INTO code_symbols ('+','.join(other)+') VALUES ('+','.join('?' for _ in other)+')', list(other.values()))
            target['symbol_key'] = None
            self.assertIsInstance(bind_gesture_context(project, Q, base, pool), GestureContext)
    def test_interface_nonmatch_and_positive_binding_drift(self):
        with tempfile.TemporaryDirectory() as t:
            project = prepare(t, sources=SOURCES); base, compact, pool = ordinary(project)
            bound = bind_gesture_context(project, Q, base, pool); self.assertIsInstance(bound, GestureContext)
            self.assertTrue(any(f['owner']['symbol_type'] == 'interface' for f in gesture_frames(project, pool, 'tile')))
            with connect(project) as db:
                db.execute("UPDATE code_symbols SET signature='interface Changed' WHERE symbol='TileState'")
            self.assertIsNone(gesture_receipt(bound))

if __name__ == '__main__': unittest.main()
