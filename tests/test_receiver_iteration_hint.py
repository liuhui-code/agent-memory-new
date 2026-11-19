import unittest
from types import SimpleNamespace
from tools.agent_memory_runtime.receiver_iteration_hint import receiver_iteration_update
from tools.agent_memory_runtime.callable_behavior_hints import callable_behavior_hints
from tools.agent_memory_runtime.receiver_iteration_hint import receiver_iteration_terms

BASE='refresh() { this.total = 0; this.rows.forEach((row: Item) => { this.total += row.value; }) }'
class ReceiverIterationHintTests(unittest.TestCase):
    def test_direct(self):
        self.assertTrue(receiver_iteration_update(BASE,'refresh'))
        self.assertTrue(receiver_iteration_update(BASE.replace('this.total = 0;','').replace('this.total += row.value;', 'this.a += row.x; this.b += row.y;'),'refresh'))
    def test_unknown_and_nonmatching(self):
        for s in [BASE.replace('+=','='), BASE.replace('row.value','other.value'),
                  BASE.replace('this.total += row.value;', 'queueMicrotask(() => { this.total += row.value; })'),
                  BASE.replace('this.total += row.value;', 'Text(row.value)'),
                  BASE.replace('this.total += row.value;', ''),
                  BASE.replace('refresh()', 'async refresh()'),
                  BASE.replace('this.rows.forEach', 'ForEach'),
                  BASE.replace('this.rows.forEach', 'other.rows.forEach'),
                  BASE.replace('this.total += row.value;', 'this.total += row.value; other()'),
                  BASE.replace('this.total = 0;', 'this.total = 0'), BASE.replace('row', 'this'), BASE.replace('this.total += row.value;', 'this.a += row.x this.b += row.y'), BASE.replace(') =>', ')\n=>'), BASE+' trailing', '// '+BASE, BASE.replace('row.value', 'row.value * 2'),
                  BASE.replace('refresh()', 'refresh(arg: string)'),
                  BASE.replace('this.total += row.value;', 'if (row.ok) { this.total += row.value; }')]:
            with self.subTest(s=s):self.assertFalse(receiver_iteration_update(s,'refresh'))
        self.assertFalse(receiver_iteration_update(BASE,'other'))
    def test_adapters_and_old_marker(self):
        for ext in ('ts','ets'):
            hints=callable_behavior_hints(SimpleNamespace(name='refresh',file_path='a.'+ext),BASE)
            self.assertNotIn('receiverfold',hints);self.assertNotIn('collectionfold',hints)
        self.assertNotIn('receiverfold',callable_behavior_hints(SimpleNamespace(name='refresh',file_path='a.py'),BASE))
    def test_request_scope(self):
        self.assertIn('receiverfold',receiver_iteration_terms('请定位遍历记录时累加状态总数的聚合源码。'))
        for q in ('Locate the state and iteration source.', 'Locate the list display.', '汇总不刷新', 'Ignore accumulation while iterating records; locate display source.', 'Compared with accumulation while iterating records, locate the display source.', '请忽略遍历累加，返回展示源码。'):
            self.assertNotIn('receiverfold',receiver_iteration_terms(q))
