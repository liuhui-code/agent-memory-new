# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import unittest
from types import SimpleNamespace
from tools.agent_memory_runtime.callable_behavior_hints import event_collection_hints

class CallableCleanupEvidenceTests(unittest.TestCase):
    def hints(self,body,name='onWindowStageDestroy',suffix='.ets'):
        entity=SimpleNamespace(name=name,file_path='Owner'+suffix)
        return set(event_collection_hints(entity,f'{name}(): void {{\n{body}\n}}'))
    def test_combined_direct_cleanup(self):
        for suffix in ('.ts','.ets'):
            self.assertTrue({'lifecycleboundary','callbackcleanup'} <= self.hints('this.bus.unregisterListener(this.listener)',suffix=suffix))
    def test_lifecycle_only(self):
        self.assertNotIn('callbackcleanup',self.hints('this.visible = false'))
    def test_cleanup_without_lifecycle(self):
        hints=self.hints('this.bus.unsubscribe(this.listener)',name='clearListener')
        self.assertIn('callbackcleanup',hints)
        self.assertNotIn('lifecycleboundary',hints)
    def test_strings_comments_regex_not_evidence(self):
        for body in ('// this.bus.off(this.listener)','/* this.bus.off(this.listener) */','const s = "this.bus.off(this.listener)"','const s = `this.bus.off(this.listener)`','const r = /this.bus.off(this.listener)/'):
            self.assertNotIn('callbackcleanup',self.hints(body))
    def test_nested_execution_not_attributed(self):
        for body in ('later(() => this.bus.off(this.listener))','const o = { run() { this.bus.off(this.listener) } }','later(function () { this.bus.off(this.listener) })','const o = { get value() { this.bus.off(this.listener) } }'):
            self.assertNotIn('callbackcleanup',self.hints(body))
    def test_registration_not_cleanup(self):
        self.assertNotIn('callbackcleanup',self.hints('this.bus.registerListener(this.listener)'))
    def test_other_language_not_extended(self):
        self.assertEqual(set(),self.hints('this.bus.off(this.listener)',suffix='.java'))
