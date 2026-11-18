# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Prospective reference-shaped spelling contract, not effect purity."""
import unittest
from unittest.mock import patch
from tools.agent_memory_runtime import ecma_callback_mask as mask
from tools.agent_memory_runtime import arkts_ui_behavior as op

class ReferenceInterpolationTests(unittest.TestCase):
    def legacy(self, source):
        with patch.object(op, 'callback_mask_lines', return_value=None):
            return op.extract_arkts_operation_names(source)

    def test_reference_shapes_and_multiple(self):
        for body in ['value','otherName','obj.member','$a._b',' \tobj \r\n. item\t ', 'this.member']:
            with self.subTest(body=body):
                text='const s=`fake ).rotate( ${'+body+'} ${other.name}`;\nButton().height(1);'
                self.assertEqual(['height'],op.extract_arkts_operation_names(text))
                self.assertIsNone(mask.callback_mask_lines(text.split('\n')))

    def test_unsafe_body_whole_file_fallback(self):
        bodies=['','f()','a[0]','a?.b','a+b','a/*x*/','a\\u0062','{a:1}','`inner`','"a"','a.', 'é', 'a\v', 'tag`x`']
        for body in bodies:
            text='const a=`fake ).rotate( ${good}`; const b=`${'+body+'}`; Button().height(1);'
            with self.subTest(body=body):
                self.assertEqual(self.legacy(text),op.extract_arkts_operation_names(text))
        text='const s=`${router.pushUrl({})}`;'
        self.assertEqual(['pushUrl'],op.extract_arkts_operation_names(text))

    def test_escape_parity(self):
        for count in range(1,5):
            text='const s=`fake ).rotate( '+'\\'*count+'${call()}`;'
            with self.subTest(count=count):
                self.assertEqual([] if count%2 else self.legacy(text),op.extract_arkts_operation_names(text))
        self.assertEqual([],op.extract_arkts_operation_names('const s=`escaped \\` fake ).rotate( ${x}`;'))

    def test_outer_tag_preserved_nested_tag_rejected(self):
        text='router.pushUrl({})`fake ).rotate( ${obj.item}`;'
        self.assertEqual(['pushUrl'],op.extract_arkts_operation_names(text))
        view='\n'.join(mask.callback_mask_lines([text],allow_reference_interpolation=True))
        self.assertTrue(view.startswith('router.pushUrl({})'))
        text='const s=`fake ).rotate( ${tag`nested`}`;'
        self.assertEqual(self.legacy(text),op.extract_arkts_operation_names(text))

    def test_unclosed_and_bounded_close(self):
        for text in ['`fake ).rotate( ${value', '`fake ).rotate( ${value}', '`'+('x'*65536)+'${value}`']:
            with self.subTest(text=text[:35]):
                self.assertEqual(self.legacy(text),op.extract_arkts_operation_names(text))
        self.assertIsNone(mask.template_end('`${abc}`',0,6,allow_reference_interpolation=True))

    def test_default_and_explicit_false_equivalence(self):
        for text in ['`plain`','`${x}`','`${obj.x}`','`${f()}`','`\\${f()}`','/*x*/ Button().rotate(1);','const r=/x/;','"unclosed']:
            with self.subTest(text=text):
                self.assertEqual(mask.callback_mask_lines([text]),mask.callback_mask_lines([text],allow_reference_interpolation=False))
                if text.startswith('`'):
                    self.assertEqual(mask.template_end(text,0,len(text)),mask.template_end(text,0,len(text),allow_reference_interpolation=False))
