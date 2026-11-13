# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

import unittest
from tools.agent_memory_runtime.context_callback_binding import binding_context_range
from tools.agent_memory_runtime.ecma_callable_ranges import property_callback_ranges


class CallbackBindingContextTests(unittest.TestCase):
    def expand(self, source, **kwargs):
        lines=source.splitlines()
        selected=next(x for x in property_callback_ranges(lines) if x['symbol']=='execute')
        selected.update(kwargs.pop('range_update',{}))
        return binding_context_range(kwargs.pop('suffix','.ets'),lines,selected,kwargs.pop('max_lines',40),kwargs.pop('budget',1500))

    def test_array_object_keeps_scalar_and_callback(self):
        source="const actions = [{\n  caption: 'Proceed',\n  execute: () => {\n    run()\n  }\n}]"
        for suffix in ['.ets','.ts','.js']:
            result=self.expand(source,suffix=suffix)
            self.assertEqual((1,6),(result['start_line'],result['end_line']))
            self.assertEqual('execute',result['symbol'])
            self.assertEqual('callback_binding_context',result['selection_reason'])

    def test_named_object_and_other_scalar_types(self):
        for value in ['true','false','null','12','-2.5','1e3',"'a,{b}'",'"escaped \\" quote"']:
            source='const action = {\n  value: '+value+',\n  execute: () => {\n  }\n}'
            self.assertIsNotNone(self.expand(source))

    def test_neighbor_object_scalar_does_not_count(self):
        source="const actions = [{\n caption: 'Other'\n}, {\n execute: () => {\n }\n}]"
        self.assertIsNone(self.expand(source))

    def test_nearest_second_object_only(self):
        source="const actions = [{\n caption: 'Other'\n}, {\n caption: 'Current',\n execute: () => {\n }\n}]"
        self.assertEqual(3,self.expand(source)['start_line'])

    def test_nested_scalar_spread_computed_getter_and_shorthand_rejected(self):
        for member in ["nested: { caption: 'wrong' }",'...other',"[name]: 'wrong'", "get name() { return 'wrong' }",'name']:
            self.assertIsNone(self.expand('const action = {\n '+member+',\n execute: () => {\n }\n}'))

    def test_class_field_and_class_method_context_not_object(self):
        self.assertIsNone(self.expand("class Action {\n caption: 'Wrong';\n execute = () => {\n }\n}"))
        self.assertIsNone(self.expand("class Action {\n caption: 'Wrong',\n execute: () => {\n }\n}"))

    def test_fake_callback_in_comment_or_template_rejected(self):
        for wrapper in ['/*\n%s\n*/','const message = `\n%s\n`;']:
            source = wrapper % "const action = {\n caption: 'Fake',\n execute: () => {\n }\n}"
            self.assertEqual([], property_callback_ranges(source.splitlines()))
            # Even a caller-supplied legacy range cannot bind this non-code object.
            selected = {'symbol': 'execute', 'start_line': 4, 'end_line': 5,
                        'selection_reason': 'ecma_property_callback_window'}
            self.assertIsNone(binding_context_range('.ets', source.splitlines(), selected, 40, 1500))

    def test_fake_scalar_in_comment_does_not_count(self):
        self.assertIsNone(self.expand("const action = {\n /* caption: 'Fake', */\n execute: () => {\n }\n}"))

    def test_existing_constraints_and_limits(self):
        source="const action = {\n caption: 'Real',\n execute: () => {\n }\n}"
        for reason in ['selected_log_event_owner','bounded_callable_primary','callable_symbol_range']:
            self.assertIsNone(self.expand(source,range_update={'selection_reason':reason}))
        self.assertIsNone(self.expand(source,budget=len(source)-1))
        self.assertIsNotNone(self.expand(source,budget=len(source)))
        self.assertIsNone(self.expand(source,max_lines=4))
        self.assertIsNone(self.expand(source,suffix='.py'))

    def test_unclosed_object_rejected(self):
        self.assertIsNone(self.expand("const action = {\n caption: 'Real',\n execute: () => {\n }\n"))

    def test_control_method_and_return_newline_blocks_rejected(self):
        for prefix in ['if (ready) {', 'function method() {', 'return\n{']:
            self.assertIsNone(self.expand(prefix+"\n caption: 'Fake',\n execute: () => {\n }\n}"))

    def test_callback_expression_suffix_not_silently_accepted(self):
        self.assertIsNone(self.expand("const action = {\n caption: 'Real',\n execute: () => {\n } + other\n}"))

    def test_scalar_only_in_callback_body_not_sibling(self):
        self.assertIsNone(self.expand("const action = {\n execute: () => {\n const inner = {caption: 'Fake'}\n }\n}"))


if __name__=='__main__':
    unittest.main()
