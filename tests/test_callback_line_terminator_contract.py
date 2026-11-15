# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import unittest
from tools.agent_memory_runtime.ecma_callable_ranges import property_callback_ranges, member_callback_ranges
from tools.agent_memory_runtime.arkts_source_ranges import arkts_line_ranges
from pathlib import Path

PROPERTY = "const actions = [{\n  caption: 'Proceed',\n  execute: () => {\n    Button().onClick(run)\n  }\n}]\n"
MEMBER = "class View {\n build() {\n Button().onClick(() => {\n  run()\n })\n }\n}\n"

class CallbackLineTerminatorContract(unittest.TestCase):
    def test_property_coordinates_ignore_line_terminators(self):
        for sep in ('\n','\r\n'):
            source=PROPERTY.replace('\n',sep)
            expected=property_callback_ranges(source.splitlines())
            self.assertEqual((3,5),(expected[0]['start_line'],expected[0]['end_line']))
            self.assertEqual(expected,property_callback_ranges(source.splitlines(keepends=True)))

    def test_member_coordinates_ignore_line_terminators(self):
        for sep in ('\n','\r\n'):
            source=MEMBER.replace('\n',sep)
            expected=member_callback_ranges(source.splitlines())
            self.assertEqual((3,5),(expected[0]['start_line'],expected[0]['end_line']))
            self.assertEqual(expected,member_callback_ranges(source.splitlines(keepends=True)))

    def test_excerpt_range_extractor_keeps_real_callback_body(self):
        lines=PROPERTY.splitlines(keepends=True)
        ranges=arkts_line_ranges(lines)
        selected=[x for x in ranges if x['symbol']=='execute']
        self.assertEqual(1,len(selected))
        self.assertEqual((3,5),(selected[0]['start_line'],selected[0]['end_line']))
        self.assertIn('Button().onClick(run)', ''.join(lines[selected[0]['start_line']-1:selected[0]['end_line']]))
