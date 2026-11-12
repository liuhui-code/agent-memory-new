# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

import unittest
from copy import deepcopy
from tools.agent_memory_runtime.context_directory_role import excluded_directory_role
from tools.agent_memory_runtime.context_code_exclusions import project_code_exclusions

QUERY='Find the shipment action handler, not view.'

def anchor(path, **extra):
    return dict(file_path=path,symbol='execute',**extra)


class ContextDirectoryRoleTests(unittest.TestCase):
    def project(self, query=QUERY, second='src/views/ShipmentList.ts', **kwargs):
        anchors=[anchor('src/actions/ShipmentAction.ts'),anchor(second)]
        raw=kwargs.pop('raw',deepcopy(anchors))
        return project_code_exclusions(anchors,query,raw,kwargs.pop('logs',[]),kwargs.pop('path',{}))

    def test_independent_action_view_fixture(self):
        for segment in ['view','views','Views']:
            result=self.project(second='src/'+segment+'/ShipmentList.ts')
            self.assertEqual(['src/actions/ShipmentAction.ts'],[x['file_path'] for x in result])

    def test_only_complete_directory_segment(self):
        for path in ['src/reviews/ShipmentList.ts','src/preview/ShipmentList.ts','src/myviews/ShipmentList.ts',
                     'src/ui/ViewsWidget.ts','src/ui/views.ts','src/views-widget/ShipmentList.ts']:
            self.assertFalse(excluded_directory_role(QUERY,anchor(path)))
            self.assertEqual(2,len(self.project(second=path)))

    def test_no_negative_query_unchanged(self):
        self.assertEqual(2,len(self.project(query='Find shipment action handler')))

    def test_no_unproved_role_pluralization(self):
        for role, directory in [('page','pages'),('service','services'),('data','datas'),('config','configs'),('metadata','metadata')]:
            self.assertFalse(excluded_directory_role('Find handler, not '+role,anchor('src/'+directory+'/ShipmentList.ts')))

    def test_positive_role_or_named_file_conflict_preserved(self):
        for target in ['view','views','src/views/ShipmentList.ts','ShipmentList.ts','ShipmentList']:
            query='Find '+target+', not view.'
            self.assertFalse(excluded_directory_role(query,anchor('src/views/ShipmentList.ts')))
            self.assertEqual(2,len(self.project(query=query)))

    def test_positive_owner_conflict_blocks_raw_compact_disagreement(self):
        query='Find CargoPanel, not view.'
        raw=[anchor('src/actions/ShipmentAction.ts'),anchor('src/views/ShipmentList.ts',owner_name='CargoPanel')]
        self.assertEqual(2,len(self.project(query=query,raw=raw)))

    def test_positive_view_with_negative_service_does_not_activate(self):
        self.assertFalse(excluded_directory_role('Find View, not service.',anchor('src/views/ShipmentList.ts')))

    def test_all_excluded_keeps_original(self):
        anchors=[anchor('src/views/First.ts'),anchor('src/views/Second.ts')]
        self.assertEqual(anchors,project_code_exclusions(anchors,QUERY,anchors,[],{}))

    def test_graph_identity_log_and_path_obligations_preserved(self):
        for flag in ['identity_match','log_identity_match','graph_neighbor','graph_relation']:
            raw=[anchor('src/actions/ShipmentAction.ts'),anchor('src/views/ShipmentList.ts',**{flag:True})]
            self.assertEqual(2,len(self.project(raw=raw)))
        for path in [{'activated':True},{'path_candidates':[{'complete':True}]}]:
            self.assertEqual(2,len(self.project(path=path)))

    def test_quoted_query_keeps_existing_policy(self):
        self.assertEqual(2,len(self.project(query='Find "shipment", not view.')))

    def test_windows_directory_separator_supported(self):
        self.assertTrue(excluded_directory_role(QUERY,anchor('src\\views\\ShipmentList.ts')))


if __name__=='__main__':
    unittest.main()
