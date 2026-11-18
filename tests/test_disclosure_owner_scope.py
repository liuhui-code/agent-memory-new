# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import unittest
from unittest.mock import patch
from tools.agent_memory_runtime.arkts_behavior_markers import extract_arkts_behavior_markers as markers

R="SymbolGlyph('arrow').rotate({angle:this.a?0:180});"
T='this.a=!this.a;'

class DisclosureOwnerScopeTests(unittest.TestCase):
    def test_distinct_owners_cannot_pair(self):
        for kind in ('class','struct'):
            self.assertNotIn('disclosurestate',markers(f'{kind} Read {{ m(){{{R}}} }} {kind} Write {{ m(){{{T}}} }}'))

    def test_same_owner_methods_and_fragment_remain(self):
        for source in (R+T,f'class Same {{ render(){{{R}}} toggle(){{{T}}} }}', f'export class Same extends Base implements API {{m(){{{R}{T}}}}}'):
            self.assertIn('disclosurestate',markers(source))

    def test_same_spelling_does_not_merge_declarations(self):
        self.assertNotIn('disclosurestate',markers(f'class Same {{m(){{{R}}}}} class Same {{m(){{{T}}}}}'))

    def test_glyph_context_is_not_borrowed(self):
        self.assertNotIn('disclosurestate',markers("class Glyph {m(){SymbolGlyph('arrow');}} class Other {m(){Box().rotate({angle:this.a?0:180});this.a=!this.a;}}"))

    def test_unknown_nested_and_unsupported_keep_legacy(self):
        for source in ('const p=/x/; '+f'class Read {{m(){{{R}}}}} class Write {{m(){{{T}}}}}',
                       f'class Outer {{m(){{{R} class Inner {{m(){{{T}}}}}}}}}',
                       f'class Read<T> {{m(){{{R}}}}} class Write {{m(){{{T}}}}}', R+T+'}'):
            self.assertIn('disclosurestate',markers(source))

    def test_inherited_receiver_keeps_legacy(self):
        source=f'class Base {{render(){{{R}}}}} class Child extends Base {{toggle(){{{T}}}}}'
        self.assertIn('disclosurestate',markers(source))

    def test_other_markers_unchanged(self):
        source=f'class Read {{m(){{{R}}}}} class Write {{m(){{{T}}}}}'
        with patch('tools.agent_memory_runtime.disclosure_owner_spans.declared_owner_spans',return_value=None):before=markers(source)
        self.assertEqual([m for m in before if m!='disclosurestate'],[m for m in markers(source) if m!='disclosurestate'])
