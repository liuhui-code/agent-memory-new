"""Self-contained exact grammar checks, not original-case evaluation."""
import unittest
from tools.agent_memory_runtime.query_ui_vertical_request import vertical_request,qualifier_matches,RESERVED


def forms(subject):
    return [f'Locate the {subject} vertical layout source.',
            f'{subject.capitalize()} records cannot scroll when their content fills the viewport. Locate the vertical layout owner.',
            f'The viewport clips {subject} records and the vertical layout does not move. Return the current code owner.']


class VerticalRequestTests(unittest.TestCase):
    def test_all_families_opaque_subjects(self):
        for subject in ('crate','parcel','shipment','ab','abcdefghijklmnopqrstuvwx','activities','quartz'):
            for query in forms(subject):
                self.assertEqual(vertical_request(query),subject,query)
    def test_subject_boundaries(self):
        for subject in ('a','a'*25,'crate2','crate_pane','crate-pane','craté','运输','Crate','CRATE'):
            self.assertIsNone(vertical_request(f'Locate the {subject} vertical layout source.'))
        for subject in ('crate','CRate','CRATE','CratePane'):
            self.assertIsNone(vertical_request(f'{subject} records cannot scroll when their content fills the viewport. Locate the vertical layout owner.'))
    def test_reserved_union_every_family(self):
        for subject in RESERVED:
            for query in forms(subject):self.assertIsNone(vertical_request(query),query)
    def test_exact_punctuation_case_and_whitespace(self):
        for query in forms('crate'):
            for bad in (query[:-1],query+' ', ' '+query,query+'\n',query+'\r',query.replace(' ', '\t',1),query.replace(' ', '  ',1),query.lower(),query.upper(),'"'+query+'"',"'"+query+"'",'`'+query+'`'):
                self.assertIsNone(vertical_request(bad),bad)
    def test_length_240_and_241_no_unparsed_padding(self):
        # No legal family reaches 240 with its independent 24-character subject cap.
        q=forms('crate')[0]
        for n in (240,241):
            query=q+' '*(n-len(q));self.assertEqual(len(query),n);self.assertIsNone(vertical_request(query))
        self.assertIsNone(vertical_request(None));self.assertIsNone(vertical_request(123));self.assertIsNone(vertical_request(b'query'))
    def test_negative_multiple_literal_named_path_and_graph(self):
        for q in ('Locate the crate and parcel vertical layout source.',
                  'Locate the crate vertical layout source, not ArticleScrollPane.',
                  'Locate the crate vertical layout source and explain logs.',
                  'Locate the crate vertical layout source and its callers.',
                  'Locate the crate vertical layout source from src/CrateLedgerPane.ets.',
                  'Locate the crate vertical layout source in CrateLedgerPane.',
                  'Locate the CrateLedgerPane vertical layout source.',
                  'Locate the ArticleScrollPane Scroll source.',
                  'Locate CodeMaker.makeCode.', 'Locate the vertical layout source.',
                  'The viewport clips activities and the vertical layout does not move. Return the current code owner.',
                  '运输记录填满屏幕后无法滑动，请返回纵向布局源码，不要分析根因。',
                  'Locate the crate vertical layout source. Locate the parcel vertical layout source.'):
            self.assertIsNone(vertical_request(q),q)
    def test_exact_identifier_part_no_stemming_or_source_permission(self):
        self.assertTrue(qualifier_matches('crate','CrateLedgerPane'))
        self.assertTrue(qualifier_matches('crate','crate'))
        for owner in ('CratesPane','CraterPane','src/CratePane.ets','Crate.Pane'):
            self.assertFalse(qualifier_matches('crate',owner))
        self.assertEqual(vertical_request(forms('activities')[0]),'activities')
        self.assertFalse(qualifier_matches('activities','ActivityPane'))
        self.assertFalse(qualifier_matches('crate',None))
