# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

import unittest
from unittest.mock import patch
from tools.agent_memory_runtime.platform_noncode_eligibility import confirmed_noncode
from tools.agent_memory_runtime.semantic_ecma_mechanisms import extract_callable_mechanisms, PLATFORM_RE


def emitted(text, baseline=False):
    lines=text.splitlines()
    if baseline:
        with patch('tools.agent_memory_runtime.semantic_ecma_mechanisms.confirmed_noncode_lines',return_value=[bytes(len(line)) for line in lines]):
            return extract_callable_mechanisms(lines,'symbol:stable',0,len(lines)-1)
    return extract_callable_mechanisms(lines,'symbol:stable',0,len(lines)-1)


def predicates(text, baseline=False):
    return [x for x in emitted(text,baseline) if x.kind=='platform_predicate']


class PlatformNoncodeEligibilityTests(unittest.TestCase):
    def test_closed_fake_strings_comments_and_plain_templates_removed(self):
        for text in ["return 'canIUse(Fake)'", 'return "hasSystemCapability(Fake)"',
                     "/*\n canIUse('Fake')\n*/", "return `canIUse(Fake)`", "return `\\${canIUse('Fake')}`"]:
            with self.subTest(text=text):
                self.assertTrue(predicates(text,True))
                self.assertEqual([],predicates(text))

    def test_all_independent_blockers_preserve_exact_baseline_mechanism(self):
        sources=["const apostrophe = /'/; return canIUse('Real')",
                 'const quote = /"/; return canIUse("Real")',
                 "const apostrophe = /'/;\nreturn canIUse('Real')",
                 'const quote = /"/;\nreturn canIUse("Real")',
                 "const obj = { return: 6 }; obj.return / canIUse('Real') / 2;",
                 "const label = 'canIUse(Fake)'; obj.return / canIUse('Real') / 2;",
                 "return `canIUse(Fake) ${canIUse('Real')}`",
                 "return `${`nested ${canIUse('Real')}`}`",
                 "return `${ { x: '}' }.x + canIUse('Real') }`",
                 "return `${ /* } */ canIUse('Real') }`",
                 "return `${ /[\"/]/.test('x') && canIUse('Real') }`",
                 "const regex = /[\\/'\"]+/; return canIUse('Real')"]
        for text in sources:
            with self.subTest(text=text):
                self.assertTrue(predicates(text,True))
                self.assertEqual(predicates(text,True),predicates(text))

    def test_true_calls_and_quoted_arguments_keep_terms_confidence_and_line(self):
        for text in ["return canIUse('SystemCapability.Feature')",
                     "const fake = 'canIUse(Fake)'; return hasSystemCapability('Real')",
                     "return canIUse('hasSystemCapability(Fake)')",
                     'return deviceInfo.deviceType', 'return ConfigurationConstant.ColorMode']:
            self.assertEqual(predicates(text,True),predicates(text))

    def test_sticky_unknown_does_not_reopen_previously_confirmed_string(self):
        text="const fake = 'canIUse(Fake)'; obj.return / canIUse('Real') / 2; 'hasSystemCapability(Unknown)'"
        scan=confirmed_noncode(text)
        starts=[m.start() for m in PLATFORM_RE.finditer(text)]
        self.assertEqual([1,0,0],[scan.noncode[i] for i in starts])
        self.assertEqual(text.index('/'),scan.unknown_start)
        self.assertEqual(predicates(text,True),predicates(text))

    def test_unclosed_regions_retroactively_unknown_from_opener(self):
        for text in ["'canIUse(Unknown)", '"canIUse(Unknown)', '/* canIUse(Unknown)', '`canIUse(Unknown)',
                     "'bad\ncanIUse(Unknown)"]:
            scan=confirmed_noncode(text)
            self.assertEqual(0,scan.unknown_start)
            self.assertFalse(any(scan.noncode))
            self.assertEqual(predicates(text,True),predicates(text))

    def test_unsupported_jsx_from_first_ambiguous_character(self):
        text="const label = 'canIUse(Fake)'; <Node text=\"x\">{canIUse('Real')}</Node>"
        scan=confirmed_noncode(text)
        self.assertEqual(text.index('<'),scan.unknown_start)
        self.assertEqual(predicates(text,True),predicates(text))

    def test_multiline_comments_preserve_later_true_line(self):
        text="/* first\n canIUse('Fake')\n last */\nreturn canIUse('Real')"
        self.assertEqual([4],[x.line for x in predicates(text)])
        self.assertEqual(predicates(text,True)[-1],predicates(text)[0])

    def test_other_mechanisms_unchanged(self):
        text="if (payload.length > maximum) {\n this.controller.restore(payload)\n this.preferences.put('key',payload)\n Button('Go').onClick(() => this.run())\n return 'canIUse(Fake)'\n}"
        self.assertEqual([x for x in emitted(text,True) if x.kind!='platform_predicate'],
                         [x for x in emitted(text) if x.kind!='platform_predicate'])

    def test_escaped_quote_and_backtick_do_not_start_interpolation(self):
        for text in ["return 'quote \\' canIUse(Fake)'", 'return `backtick \\` canIUse(Fake)`']:
            self.assertEqual([],predicates(text))

    def test_unknown_template_keeps_baseline_false_positive_limit(self):
        text="return `canIUse(Fake) ${value}`"
        scan=confirmed_noncode(text)
        self.assertEqual(text.index('`'),scan.unknown_start)
        self.assertEqual(predicates(text,True),predicates(text))


if __name__=='__main__':
    unittest.main()
