# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
from types import SimpleNamespace
import unittest
from tools.agent_memory_runtime.callable_behavior_hints import event_collection_hints

class CollectionEvidenceTests(unittest.TestCase):
    def hints(self, body, name='onTap', suffix='.ts'):
        e = SimpleNamespace(name=name, file_path='src/Owner'+suffix)
        return set(event_collection_hints(e, f'{name}(i: number) {{\n{body}\n}}'))

    def test_same_method(self):
        for suffix in ('.ts', '.ets'):
            self.assertEqual({'eventboundary','collectionwrite'}, self.hints('this.values[i] = true;',suffix=suffix))
    def test_scalar(self):
        self.assertEqual({'eventboundary'}, self.hints('this.selected = true;'))
    def test_writer_without_event(self):
        self.assertEqual({'collectionwrite'}, self.hints('this.values[i] = true;',name='setAt'))
    def test_split_methods_not_unioned(self):
        self.assertNotIn('collectionwrite',self.hints('this.selected = true;'))
        self.assertNotIn('eventboundary',self.hints('this.values[i] = true;',name='setAt'))
    def test_comment_and_string_writes(self):
        for body in ('// this.values[i] = true;', '/* this.values[i] = true; */', 'const s = "this.values[i] = true";', "const s = 'this.values[i] = true';",'const s = `this.values[i] = true`;'):
            self.assertEqual({'eventboundary'},self.hints(body))
    def test_nested_callbacks_fail_closed(self):
        for body in ('later(() => { this.values[i] = true; });','later(function () { this.values[i] = true; });','const work = () => this.values[i] = true;'):
            self.assertEqual({'eventboundary'},self.hints(body))
    def test_reads_and_comparisons_are_not_writes(self):
        for body in ('return this.values[i];','return this.values[i] === true;','return this.values[i] == true;'):
            self.assertEqual({'eventboundary'},self.hints(body))
    def test_non_ecma_no_new_labels(self):
        self.assertEqual(set(),self.hints('this.values[i] = true;',suffix='.java'))

    def test_regex_literal_is_not_a_write(self):
        self.assertEqual({'eventboundary'},self.hints(r'const r = /this.values[i] = true/;'))
    def test_nested_object_methods_are_not_owned(self):
        for body in ('const obj = { save() { this.values[i] = true; } };',
                     'const obj = { get value() { this.values[i] = true; } };',
                     'const obj = { set value(v) { this.values[i] = v; } };'):
            self.assertEqual({'eventboundary'},self.hints(body))
