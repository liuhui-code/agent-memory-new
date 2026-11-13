# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.callable_behavior_hints import event_collection_hints

class CallableStateHandoffTests(unittest.TestCase):
    def hints(self, body, name='onSelected', suffix='.ets'):
        return set(event_collection_hints(SimpleNamespace(name=name,file_path='Selection'+suffix),f'{name}(entry: Entry): void {{\n{body}\n}}'))
    def test_same_callable_conjunction(self):
        for suffix in ('.ets','.ts'):
            self.assertIn('statehandoff',self.hints('this.selected = entry.id; this.openPanel();',suffix=suffix))
    def test_partial_or_other_callable_not_unioned(self):
        for body,name in [('this.selected = entry.id;','onSelected'),('this.openPanel();','onSelected'),('this.selected = entry.id; this.openPanel();','saveSelection')]:
            self.assertNotIn('statehandoff',self.hints(body,name))
        source='class Selection { onSelected(entry) { this.selected = entry.id; } openPanel() {} }'
        self.assertNotIn('statehandoff',event_collection_hints(SimpleNamespace(name='onSelected',file_path='x.ets'),source))
    def test_non_code_and_nested_are_not_current_method(self):
        body='this.selected = entry.id; this.openPanel();'
        for source in ['// '+body, '/* '+body+' */', 'const text = "'+body+'"', 'const text = `'+body+'`', 'const r = /'+body+'/', 'later(() => { '+body+' });','const o = { run() { '+body+' } };','const o = { get value() { '+body+' } };']:
            with self.subTest(source=source):self.assertNotIn('statehandoff',self.hints(source))
    def test_comparisons_and_unverified_language_not_writes(self):
        for op in ('==','===','!=','!==','<=','>='):
            self.assertNotIn('statehandoff',self.hints(f'if (this.selected {op} entry.id) {{ this.openPanel(); }}'))
        self.assertNotIn('statehandoff',self.hints('this.selected = entry.id; this.openPanel();',suffix='.java'))

class StateHandoffPublicTests(AgentMemoryTestBase):
    def test_independent_same_method_and_explicit_controls(self):
        p=json.loads((Path(__file__).resolve().parents[1]/'docs/eval/event-validation-current/event-protocol.json').read_text())
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for f,s in p['sources'].items():(root/f).write_text(s)
            self.run_memory(root,'init');self.run_memory(root,'learn-path','--path','.')
            for name,q,required in p['queries']:
                out=json.loads(self.run_memory(root,'context','--query',q,'--compact','--json').stdout)['query_handoff']
                paths={a['file_path'] for a in out['code_anchors']}
                # Dual-owner baseline has an extra split-method owner; retention
                # is a guard only, not a claim that its existing precision passed.
                if name=='two':self.assertTrue(set(required)<=paths)
                else:self.assertEqual(set(required),paths)
                if name in ('handoff','chinese'):
                    body='\n'.join(e['content'] for a in out['code_anchors'] for e in a.get('source_excerpts',[]))
                    self.assertIn('this.currentId = entry.id',body);self.assertIn('this.openEditor()',body)
