# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Pure Development controls for existing named-result exclusion grammar."""
import unittest
from tools.agent_memory_runtime.query_language import excluded_code_candidate
from tools.agent_memory_runtime.query_callable_evidence_set import excluded_member


class NamedExclusionBoundaryTests(unittest.TestCase):
    query = 'Find the LedgerRecordPreview method, excluding LedgerRecord.'

    def check_both(self, item, expected):
        for check in (excluded_code_candidate, excluded_member):
            with self.subTest(check=check.__name__, item=item):
                self.assertEqual(expected, check(self.query, item))

    def test_exact_owner_and_file_stem(self):
        for item in ({'owner_name':'LedgerRecord'}, {'file_path':'src/LedgerRecord.ets'}):
            self.check_both(item, True)

    def test_prefix_suffix_extensions_are_distinct(self):
        for name in ('LedgerRecordPreview', 'ArchivedLedgerRecord'):
            self.check_both({'owner_name':name, 'file_path':'src/'+name+'.ets'}, False)

    def test_path_and_field_boundaries_do_not_concatenate(self):
        for item in ({'file_path':'src/Ledger/Record.ets'},
                     {'file_path':r'src\Ledger\Record.ets'},
                     {'file_path':'src/Ledger', 'owner_name':'Record'}):
            self.check_both(item, False)

    def test_hyphen_underscore_case_normalization_within_atom(self):
        for path in ('src/ledger-record.ets', 'src/ledger_record.ets', 'src/LEDGERRECORD.ets'):
            self.check_both({'file_path':path}, True)
        self.check_both({'file_path':'src/ledger-record-preview.ets'}, False)

    def test_exact_directory_remains_conservative(self):
        for path in ('src/LedgerRecord/Other.ets', r'src\LedgerRecord\Other.ets'):
            self.check_both({'file_path':path, 'owner_name':'Other'}, True)

    def test_qualified_owner_segments_not_prefixes(self):
        self.check_both({'owner_name':'Outer.LedgerRecord'}, True)
        self.check_both({'owner_name':'Outer.LedgerRecordPreview'}, False)

    def test_shared_file_keeps_conservative_file_identity(self):
        self.check_both({'file_path':'src/LedgerRecord.ets', 'owner_name':'Unrelated'}, True)
        self.check_both({'file_path':'src/Bundle.ets', 'owner_name':'LedgerRecordPreview'}, False)

    def test_role_exclusion_stays_separate(self):
        for role in ('store', 'card', 'model'):
            query='Find implementation, excluding '+role+'.'
            for check in (excluded_code_candidate, excluded_member):
                self.assertTrue(check(query, {'owner_name':'Ledger'+role.title()}))
                self.assertFalse(check(query, {'owner_name':'LedgerPreview'}))

    def test_second_caller_keeps_existing_lower_camel_symbol_scope(self):
        query='Find implementation, excluding previewTitle.'
        self.assertFalse(excluded_code_candidate(query, {'symbol':'previewTitle'}))
        self.assertTrue(excluded_member(query, {'symbol':'Outer.previewTitle'}))
        self.assertFalse(excluded_member(query, {'symbol':'previewTitleExpanded'}))

    def test_empty_candidate_never_matches(self):
        for item in ({}, {'file_path':'...///', 'owner_name':'---'}):
            self.check_both(item, False)


if __name__ == '__main__':
    unittest.main()
