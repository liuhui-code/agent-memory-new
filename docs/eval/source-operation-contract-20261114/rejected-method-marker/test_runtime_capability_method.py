# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
from types import SimpleNamespace
import unittest
from tools.agent_memory_runtime.callable_behavior_hints import callable_behavior_hints

class RuntimeCapabilityMethodTests(unittest.TestCase):
    def hints(self,body,suffix='.ets'):
        return callable_behavior_hints(SimpleNamespace(name='inspect',file_path='src/Inspection'+suffix),'inspect() { '+body+' }')
    def test_existing_api_family_is_method_local(self):
        for suffix in ('.ets','.ts'):
            for call in ('bundleManager.getBundleInfoForSelf(0)','bundleManager.getBundleInfo(0)',
                         'bundleManager.getApplicationInfo(0)','bundleManager.queryExtensionAbilityInfos(0)',
                         'canIUse("SystemCapability.Example")','hasSystemCapability("Example")'):
                self.assertIn('runtimecapability',self.hints('return '+call+';',suffix))
    def test_non_code_and_metadata_do_not_claim_operation(self):
        for body in ('return "bundleManager.getBundleInfoForSelf(0)";',
                     '// bundleManager.getBundleInfoForSelf(0)\nreturn false;',
                     '/* canIUse("Example") */ return false;',
                     'return `bundleManager.getBundleInfoForSelf(0)`;',
                     'return /bundleManager.getBundleInfoForSelf(0)/;',
                     'return { capability: "available" };',
                     'return somethingElse.getBundleInfoForSelf(0);'):
            self.assertNotIn('runtimecapability',self.hints(body),body)
    def test_nested_callable_ownership_fails_closed(self):
        for body in ('return () => bundleManager.getBundleInfoForSelf(0);',
                     'function inner() { return canIUse("Example"); }',
                     'return { inner() { return canIUse("Example"); } };',
                     'return { get ready() { return canIUse("Example"); } };',
                     'class Inner { inspect() { return canIUse("Example"); } }'):
            self.assertNotIn('runtimecapability',self.hints(body),body)
    def test_other_method_and_language_do_not_inherit_file_marker(self):
        self.assertNotIn('runtimecapability',self.hints('return false;'))
        self.assertNotIn('runtimecapability',self.hints('return canIUse("Example");','.java'))
