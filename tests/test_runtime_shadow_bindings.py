# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import unittest
from tools.agent_memory_runtime.source_operation_roles import source_operation_roles
from tools.agent_memory_runtime.query_source_operation import certify_source_operation
from tests.test_source_operation_contract import candidate,QUERY

class RuntimeShadowBindingTests(unittest.TestCase):
    def test_destructuring_and_direct_rebinding_remain_unknown(self):
        for setup in ['const {canIUse}=other;', 'let {probe:canIUse}=other;', 'const [canIUse]=other;',
                      'const {\n canIUse\n}=other;', '({canIUse}=other);', '[canIUse]=other;',
                      'canIUse=localPredicate;', 'canIUse ||= fallback;', 'canIUse ??= fallback;']:
            roles=source_operation_roles('inspect(){'+setup+'return canIUse("X");}','x.ts')
            with self.subTest(setup=setup):
                self.assertIn('source_operation_unresolved:runtimecapability',roles)
                self.assertNotIn('source_operation:runtimecapability',roles)
                rows=[candidate('runtimecapability'),candidate()];rows[1]['callable_roles']=roles
                certify_source_operation(rows,QUERY)
                self.assertFalse(any(r.get('source_operation_match') for r in rows))
    def test_bundle_and_system_api_bindings(self):
        for source in ['inspect(){const {bundleManager}=other;return bundleManager.getBundleInfoForSelf(0);}',
                       'inspect(){bundleManager=other;return bundleManager.getBundleInfoForSelf(0);}',
                       'inspect(){const {hasSystemCapability}=other;return hasSystemCapability("X");}']:
            roles=source_operation_roles(source,'x.ets')
            self.assertIn('source_operation_unresolved:runtimecapability',roles)
            self.assertNotIn('source_operation:runtimecapability',roles)
    def test_strings_comments_and_other_bindings_do_not_block_direct_syntax(self):
        for setup in ['const {other}=local;', '// canIUse=local\n', 'const label="const {canIUse}=local";', 'if (other === canIUse) {}']:
            roles=source_operation_roles('inspect(){'+setup+'return canIUse("X");}','x.ts')
            self.assertIn('source_operation:runtimecapability',roles)

    def test_pre_fix_v2_roles_do_not_reuse_unsafe_proof(self):
        for prior in ['source_operation_checked:v1','source_operation_checked:v2']:
            rows=[candidate('runtimecapability'),candidate()]
            rows[0]['callable_roles']=[prior,'source_operation:runtimecapability']
            certify_source_operation(rows,QUERY)
            self.assertFalse(any(r.get('source_operation_match') for r in rows))
