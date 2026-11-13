# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json
import tempfile
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
from tests.test_salient_source_public import SOURCES
from tools.agent_memory_runtime.query_code_selection import structural_boundary_query, preserve_structural_boundary_neighbors

class StructuralExclusionTests(AgentMemoryTestBase):
    def test_negative_structure_does_not_request_graph(self):
        for query in ('Locate retry handler; exclude generated build artifacts.',
                      'Find update owner, rather than native package output.',
                      '定位状态更新，排除构建产物。'):
            self.assertFalse(structural_boundary_query(query), query)
        for query in ('Locate native build imports; exclude generated copies.',
                      'Find package configuration and source.', '定位原生构建边界，排除示例。'):
            self.assertTrue(structural_boundary_query(query), query)
    def test_existing_positive_query_fallback_is_not_redefined(self):
        # Existing fallback and named-identifier retention stay fail-open.
        self.assertTrue(structural_boundary_query('exclude build artifacts'))
        self.assertTrue(structural_boundary_query('Find handler; exclude NativeBuildCache.'))

    def test_positive_graph_relation_preserved_and_negative_not_added(self):
        owner={'file_path':'ui/Owner.ets'}
        neighbor={'file_path':'app/Registry.ets','match_reasons':['graph_neighbor','graph_relation:imports']}
        self.assertEqual([owner],preserve_structural_boundary_neighbors([owner],[neighbor],'Find owner; exclude build artifacts.'))
        self.assertEqual([owner,neighbor],preserve_structural_boundary_neighbors([owner],[neighbor],'Find native build imports; exclude examples.'))
    def test_public_exclusion_does_not_create_structural_target(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            files=dict(SOURCES)
            files['src/ui/RestoreView.ets']=files['src/ui/RestoreView.ets'].replace('enableRecovery','enableCapacityRecovery').replace('statusMessage','notice')
            files['src/app/ScreenRegistry.ets']="import { RestoreView } from '../ui/RestoreView'\nexport function registerScreens(): string {\n return 'registered'\n}\n"
            for name,text in files.items():
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
            self.run_memory(root,'init');self.run_memory(root,'learn-path','--path','.')
            base='Locate RestoreView.enableCapacityRecovery handler that enables retry and updates the notice'
            for query in (base+'.',base+'; exclude generated build artifacts.'):
                h=json.loads(self.run_memory(root,'context','--query',query,'--compact','--json').stdout)['query_handoff']
                self.assertEqual({'src/ui/RestoreView.ets'},{a['file_path'] for a in h['code_anchors']})
                body=' '.join(e['content'] for a in h['code_anchors'] for e in a.get('source_excerpts',[]))
                self.assertIn('this.retryAllowed = true',body)
            positive=base+' native build imports and source.'
            for compact in (False,True):
                args=['context','--query',positive,'--json']+(['--compact'] if compact else [])
                h=json.loads(self.run_memory(root,*args).stdout)['query_handoff']
                self.assertIn('src/app/ScreenRegistry.ets',{a['file_path'] for a in h['code_anchors']})
            queries={
                'Locate both RestoreView.enableCapacityRecovery and NoticePreferences.save source.':{'src/ui/RestoreView.ets','src/ui/NoticePreferences.ets'},
                'Locate the caller and emitter of the ordinary log message notice update dispatched.':{'src/ui/NoticePreferences.ets','src/services/NoticeService.ets'},
            }
            for query,expected in queries.items():
                h=json.loads(self.run_memory(root,'context','--query',query,'--compact','--json').stdout)['query_handoff']
                self.assertTrue(expected <= {a['file_path'] for a in h['code_anchors']})
