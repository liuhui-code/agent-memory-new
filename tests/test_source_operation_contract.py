# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import copy
import unittest
from tools.agent_memory_runtime.source_operation_roles import source_operation_roles
from tools.agent_memory_runtime.query_source_operation import certify_source_operation

CHECKED='source_operation_checked:v2.1'
def candidate(proof=None, **values):
    return dict(start_line=1,end_line=5,symbol_key='symbol:fixture',source_digest='digest',
                file_path='src/Fixture.ets',semantic_adapter='arkts-static@1.2',
                evidence_class='static',callable_roles=[CHECKED]+([f'source_operation:{proof}'] if proof else []),**values)
QUERY='Locate executable runtime capability inspection source.'

class SourceOperationContractTests(unittest.TestCase):
    def test_producer_source_not_strings_comments_or_identifier_names(self):
        for code in ['return bundleManager.getBundleInfoForSelf(0);','return canIUse("Example");']:
            self.assertIn('source_operation:runtimecapability',source_operation_roles('inspect() {'+code+'}','x.ets'))
        for code in ['return "bundleManager.getBundleInfoForSelf(0)";',
                     '/* canIUse("Example") */ return false;',
                     'const runtimecapability=true; return runtimecapability;']:
            self.assertEqual([CHECKED],source_operation_roles('inspect(){'+code+'}','x.ts'))
    def test_possible_nested_or_regex_operation_is_unknown_not_absent(self):
        for body in ['const f=()=>canIUse("X");','return { get ready() { return canIUse("X"); } };',
                     'function other(){ return canIUse("X"); }','return /canIUse(x)/;', 'return `${canIUse("X")}`;', 'const f=()=>`${canIUse("X")}`;']:
            self.assertIn('source_operation_unresolved:runtimecapability',source_operation_roles('inspect(){'+body+'}','x.ets'))
        self.assertEqual([],source_operation_roles('inspect(){ return canIUse("X"); }','x.java'))
    def test_source_priority_does_not_change_score(self):
        rows=[candidate('runtimecapability',score=1),candidate(score=99)]
        certify_source_operation(rows,QUERY)
        self.assertTrue(rows[0].get('source_operation_match'));self.assertEqual(1,rows[0]['score'])
    def test_old_unknown_unproved_and_two_real_owners_block_exclusivity(self):
        blockers=[candidate('runtimecapability'),candidate(),candidate(),candidate()]
        blockers[1]['callable_roles']=[]
        blockers[2]['callable_roles']=[CHECKED,'source_operation_unresolved:runtimecapability']
        blockers[3]['callable_roles']=['source_operation:runtimecapability']
        for other in blockers:
            rows=[candidate('runtimecapability'),other]
            certify_source_operation(rows,QUERY)
            self.assertFalse(any(r.get('source_operation_match') for r in rows))
    def test_false_marker_and_missing_bounds_cannot_grant_priority(self):
        for row in [candidate('not_a_real_marker'),candidate()]:
            certify_source_operation([row],QUERY);self.assertFalse(row.get('source_operation_match'))
        row=candidate('runtimecapability');row['end_line']=None
        certify_source_operation([row],QUERY);self.assertFalse(row.get('source_operation_match'))
    def test_explicit_literal_declaration_and_mixed_requests_are_not_source_priority(self):
        queries=['Find runtime capability text.', 'Find runtime capability declaration.',
                 'Find runtime capability manifest metadata.', 'Find runtime capability source and settings.',
                 'Find both runtime capability owners.', 'Locate `runtime capability` source.']
        for query in queries:
            rows=[candidate('runtimecapability'),candidate()]
            certify_source_operation(rows,query);self.assertFalse(any(r.get('source_operation_match') for r in rows),query)
        for key in ['typed_contract_match','explicit_owner_identity_match']:
            rows=[candidate('runtimecapability'),candidate(**{key:True})]
            certify_source_operation(rows,QUERY);self.assertFalse(any(r.get('source_operation_match') for r in rows))
    def test_restore_scope_abstention_blocks_unrelated_reader_regression(self):
        source=source_operation_roles('onCreate(){ const entries=preferences.get("x"); use(()=>entries); }','Bootstrap.ets')
        rows=[candidate('persistenceread'),candidate()];rows[1]['callable_roles']=source
        certify_source_operation(rows,'Find preference restore source.')
        self.assertFalse(any(r.get('source_operation_match') for r in rows))

    def test_partial_supported_or_unsupported_conjunction_is_not_full_proof(self):
        rows=[candidate('runtimecapability'),candidate()]
        certify_source_operation(rows,'Locate runtime capability source that restores preferences.')
        self.assertFalse(any(r.get('source_operation_match') for r in rows))

    def test_missing_or_unbalanced_body_is_unknown(self):
        self.assertEqual([],source_operation_roles('inspect();','x.ets'))
        self.assertEqual([],source_operation_roles('inspect(){ return false;','x.ets'))

    def test_query_reuse_and_json_roundtrip_do_not_reuse_authority(self):
        import json
        for roundtrip in (False,True):
            rows=[candidate('runtimecapability'),candidate()]
            certify_source_operation(rows,QUERY)
            self.assertTrue(rows[0].get('source_operation_match'))
            if roundtrip: rows=json.loads(json.dumps(rows))
            certify_source_operation(rows,'Find runtime capability text.')
            self.assertFalse(any(r.get('source_operation_match') for r in rows))

    def test_unverified_language_or_adapter_is_unknown(self):
        for field,value in [('file_path','Fixture.java'),('semantic_adapter','external@1')]:
            rows=[candidate('runtimecapability'),candidate()];rows[1][field]=value
            certify_source_operation(rows,QUERY)
            self.assertFalse(any(r.get('source_operation_match') for r in rows))

    def test_invalid_or_graph_competitor_cannot_be_counted_as_absent(self):
        for field,value in [('end_line',None),('graph_depth',1)]:
            rows=[candidate('runtimecapability'),candidate('runtimecapability')];rows[1][field]=value
            certify_source_operation(rows,QUERY)
            self.assertFalse(any(r.get('source_operation_match') for r in rows))
    def test_obvious_shadowing_and_other_receiver_are_unresolved(self):
        for code in ['inspect(){ return arbitrary.canIUse("X"); }',
                     'inspect(){ const canIUse=localPredicate; return canIUse("X"); }',
                     'inspect(canIUse: Function){return canIUse("X");}']:
            self.assertIn('source_operation_unresolved:runtimecapability',source_operation_roles(code,'x.ts'))

    def test_dynamic_optional_and_local_alias_reads_are_unresolved_competitors(self):
        from unittest.mock import patch
        bodies=["return preferences['get']('x');", 'return prefs?.get("x");',
                'return preferences?.get("x");', 'const alias=preferences; return alias.get("x");',
                'const read=preferences.get; return read("x");', 'return externalAlias.read("x");']
        for body in bodies:
            roles=source_operation_roles('inspect(){'+body+'}','x.ets')
            self.assertIn('source_operation_unresolved:persistenceread',roles,body)
            self.assertNotIn('source_operation:persistenceread',roles,body)
            rows=[candidate('persistenceread'),candidate()];rows[1]['callable_roles']=roles
            # Existing restore concept is composite and already abstains. Also
            # exercise the source-competition gate under a single requested read.
            with patch('tools.agent_memory_runtime.query_source_operation.behavior_marker_terms',return_value=['persistenceread']):
                certify_source_operation(rows,'Locate persistence read source.')
            self.assertFalse(any(row.get('source_operation_match') for row in rows),body)
    def test_old_v1_checked_absence_is_unknown_to_v2_consumer(self):
        rows=[candidate('runtimecapability'),candidate()]
        rows[1]['callable_roles']=['source_operation_checked:v1']
        certify_source_operation(rows,QUERY)
        self.assertFalse(any(row.get('source_operation_match') for row in rows))
