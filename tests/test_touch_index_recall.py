import copy
import unittest
from tools.agent_memory_runtime.query_touch_index_recall import (
    TouchRecall, recall_projection, projected_method_terms, TERMS,
)

Q = '请定位触摸回调和索引读取所在源码。'

class TouchRecallTests(unittest.TestCase):
    def test_disabled_and_custom_port(self):
        self.assertIsNone(recall_projection(Q))
        self.assertIsNone(recall_projection(Q, object(), allow_touch_recall=True))

    def test_private_exact_binding(self):
        p = recall_projection(Q, allow_touch_recall=True)
        self.assertIsInstance(p, TouchRecall)
        self.assertTrue(p.valid_for('ontouch touches', Q))
        self.assertFalse(p.valid_for(Q, Q + '。'))
        self.assertFalse(p.valid_for(Q + '。', Q))
        self.assertFalse(copy.copy(p).valid_for('ontouch touches', Q))
        self.assertFalse(copy.deepcopy(p).valid_for('ontouch touches', Q))
        self.assertFalse(TouchRecall(Q, Q, TERMS, object()).valid_for(Q, Q))
        self.assertFalse(TouchRecall(Q, Q, ('other',), p.issuer).valid_for(Q, Q))

    def test_fixed_terms_only(self):
        p = recall_projection(Q, allow_touch_recall=True)
        terms = projected_method_terms('ontouch touches', p, Q)
        self.assertTrue(all(t in terms for t in TERMS))
        self.assertNotIn('error', terms)

    def test_unsupported_exact_legacy(self):
        for q in ('Locate the touch callback and first pointer access source.',
                  '请不要返回触摸回调和索引读取所在源码。',
                  '请定位 TouchOwner 的触摸回调和索引读取所在源码。'):
            self.assertEqual(recall_projection(q), recall_projection(q, allow_touch_recall=True))

    def test_existing_projection_priority(self):
        q = 'Locate the UI rendering cleanup owner.'
        old = recall_projection(q, allow_render_recall=True)
        new = recall_projection(q, allow_render_recall=True, allow_touch_recall=True)
        self.assertEqual(type(old), type(new))
        self.assertEqual(old, new)
