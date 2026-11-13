# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json
import tempfile
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.query_log_admission import compatible_opaque_template

EVIDENCE=Path(__file__).resolve().parents[1]/'docs/evidence/opaque-template-followup'
PROTOCOL=json.loads((EVIDENCE/'protocol.json').read_text())


class OpaqueTemplateCompactTests(AgentMemoryTestBase):
    def test_public_template_fixed_and_missing_controls(self):
        for suffix in ('.ts','.ets'):
            with tempfile.TemporaryDirectory() as directory:
                project=Path(directory)
                for name,source in PROTOCOL['sources'].items():
                    (project/Path(name).with_suffix(suffix)).write_text(source)
                self.run_memory(project,'init');self.run_memory(project,'learn-path','--path','.')
                for index,case in enumerate(PROTOCOL['queries']):
                    raw=json.loads(self.run_memory(project,'context','--query',case['query'],'--json').stdout)['query_handoff']
                    compact=json.loads(self.run_memory(project,'context','--query',case['query'],'--compact','--json').stdout)['query_handoff']
                    with self.subTest(suffix=suffix,index=index):
                        templates=[item['message_template'] for item in compact['log_anchors']]
                        expected=case['required_template']
                        self.assertEqual([expected] if expected else [],templates)
                        self.assertEqual([item['message_template'] for item in raw['log_anchors']],templates)
                        self.assertEqual(raw['path_context']['activated'],compact['path_context']['activated'])
                        if index==0:
                            self.assertFalse(compact['path_context']['activated'])
                            self.assertEqual([],compact['path_context']['path_candidates'])
                            self.assertNotIn('DELIVERY_EVENT_59D3',str(compact['log_anchors']))
                            self.assertEqual({'rejected'},{a['symbol'] for a in compact['code_anchors']})

    def test_literal_gap_controls(self):
        for template,query,expected in [
            ('parcel code=${id}','parcel code=EVENT_73AB',True),
            ('parcel code=${id}; status=${status}','parcel code=EVENT_73AB; status=bad',True),
            ('parcel code=${id}; status=${status}','parcel code=EVENT_73AB',False),
            ('${id}','EVENT_73AB',False),
            ('parcel code=${id}','unknown EVENT_73AB',False),
            ('parcel code=${id}','parcel code=plain',False),
            ('parcel code=${id}','parcel code=123456789',False),
            ('parcel code=${id}','parcel code=ABCDEFGH',False),
            ('parcel code=${id}','parcel code=e73',False),
            ('before ${id} after','after EVENT_73AB before',False),
            ('EVENT_73AB parcel','EVENT_73AB parcel',False),
            ('parcel ${x}${id} done','parcel EVENT_73AB done',True),
        ]:
            with self.subTest(template=template,query=query):
                self.assertEqual(expected,compatible_opaque_template({'message_template':template},query))

    def test_same_template_keeps_both_source_owners_unbound(self):
        with tempfile.TemporaryDirectory() as directory:
            project=Path(directory)
            original=PROTOCOL['sources']['ParcelTrace.ts']
            (project/'ParcelTrace.ts').write_text(original)
            (project/'BackupTrace.ts').write_text(original.replace('ParcelTrace','BackupTrace'))
            self.run_memory(project,'init');self.run_memory(project,'learn-path','--path','.')
            query=PROTOCOL['queries'][0]['query']
            compact=json.loads(self.run_memory(project,'context','--query',query,'--compact','--json').stdout)['query_handoff']
            self.assertEqual({'ParcelTrace.ts','BackupTrace.ts'},{item['file_path'] for item in compact['log_anchors']})
            self.assertEqual({'ParcelTrace.ts','BackupTrace.ts'},{item['file_path'] for item in compact['code_anchors']})
            self.assertFalse(compact['path_context']['activated'])
            self.assertEqual([],compact['path_context']['path_candidates'])

    def test_short_literal_gap_is_not_an_event_identity(self):
        from tools.agent_memory_runtime.log_event_identity import event_match
        template='code=${event}'
        query='Locate code=DELIVERY_EVENT_59D3'
        self.assertTrue(compatible_opaque_template({'message_template':template},query))
        self.assertEqual(0,event_match({'message_template':template},query)['priority'])
        with tempfile.TemporaryDirectory() as directory:
            project=Path(directory)
            for name in ('FirstTrace','SecondTrace'):
                (project/(name+'.ts')).write_text('export class '+name+' {\n  emit(event: string): void {\n    console.error(`code=${event}`)\n  }\n}\n')
            self.run_memory(project,'init');self.run_memory(project,'learn-path','--path','.')
            compact=json.loads(self.run_memory(project,'context','--query',query,'--compact','--json').stdout)['query_handoff']
            self.assertEqual({'FirstTrace.ts','SecondTrace.ts'},{item['file_path'] for item in compact['log_anchors']})
            self.assertFalse(compact['path_context']['activated'])
