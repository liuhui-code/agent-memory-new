# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json
import tempfile
import unittest
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
from tests.test_nested_callable_identity import SOURCE
from tools.agent_memory_runtime.context_compact import relevant_relations, compact_code_anchor, merge_anchor_evidence
from tools.agent_memory_runtime.query_handoff import code_anchors

QUERY='Locate the component method that validates the empty name and returns before dispatching updates.'
class TypedReferencePublicTests(AgentMemoryTestBase):
    def test_file_projection_keeps_real_import_relation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'src/pages').mkdir(parents=True);(root/'src/services').mkdir(parents=True)
            (root/'src/pages/PreferenceEditor.ets').write_text(SOURCE)
            (root/'src/services/PreferenceApi.ets').write_text('export class PreferenceApi {\n dispatchUpdate(value: string): void {\n console.info(`submit preference update ${value}`)\n }\n}\n')
            self.run_memory(root,'init');self.run_memory(root,'learn-path','--path','.')
            raw=json.loads(self.run_memory(root,'context','--query',QUERY,'--json').stdout)
            compact=json.loads(self.run_memory(root,'context','--query',QUERY,'--compact','--json').stdout)
            imports=[e for e in raw['edge_matches'] if e['relation']=='imports']
            self.assertEqual(1,len(imports))
            anchor=next(a for a in raw['query_handoff']['code_anchors'] if a['file_path']=='src/pages/PreferenceEditor.ets')
            file=next(f for f in self.list_records(root,'code-file') if f['file_path']==anchor['file_path'])
            self.assertEqual(file['id'],anchor['record_id'])
            self.assertEqual(imports[0]['source_id'],file['id'])
            # Same numeric symbol ID exists but is NOT this callable identity.
            symbols=self.list_records(root,'code-symbol')
            collision=next(s for s in symbols if s['id']==file['id'])
            self.assertNotEqual('commitPreference',collision['symbol'])
            self.assertTrue(any(e['relation']=='imports' and e['source_type']=='code_file' and e['source_id']==file['id'] for e in compact['query_handoff']['relation_hints']))
            self.assertLessEqual(compact['output_budget']['estimated_tokens'],1500)

class TypedReferenceUnitTests(unittest.TestCase):
    def test_collision_unknown_and_correct_endpoints(self):
        edges=[{'source_type':t,'source_id':7,'relation':'calls','target_type':'code_symbol','target_id':99} for t in ('code_file','code_symbol','code_log_statement')]
        for t in ('code_file','code_symbol','code_log_statement'):
            out=relevant_relations(edges,[{'record_refs':[[t,7]]}],[])
            self.assertEqual([t],[e['source_type'] for e in out])
        self.assertEqual([],relevant_relations(edges,[{'record_id':7,'record_ids':[7]}],[]))
        self.assertEqual(['code_log_statement'],[e['source_type'] for e in relevant_relations(edges,[],[{'log_id':7}])])
    def test_types_survive_projection_and_merging(self):
        wiki=[{'kind':k,'id':7,'file_path':'Owner.ts','symbol':s,'symbol_type':t,'start_line':1,'end_line':4} for k,s,t in [('file','Owner','class'),('symbol','run','function')]]
        raw=code_anchors(wiki,[])
        projected=[compact_code_anchor(a) for a in raw]
        merge_anchor_evidence(projected[0],projected[1])
        self.assertEqual([['code_file',7],['code_symbol',7]],projected[0]['record_refs'])

    def test_homogeneous_ids_and_unknown_merge_keep_compatibility(self):
        target=compact_code_anchor({'record_id':7,'record_type':'code_symbol','file_path':'A.ts'})
        self.assertEqual([7],target['record_ids'])
        self.assertEqual('code_symbol',target['record_type'])
        merge_anchor_evidence(target,{'record_ids':[8]})
        self.assertEqual([7,8],target['record_ids'])
        self.assertNotIn('record_type',target)
        self.assertEqual([['code_symbol',7]],target['record_refs'])
        edge={'source_type':'code_symbol','source_id':8,'relation':'calls','target_type':'code_symbol','target_id':99}
        self.assertEqual([],relevant_relations([edge],[target],[]))
    def test_direct_and_wrapped_logs_preserve_distinct_provenance(self):
        raw=code_anchors([], [{'id':4,'file_path':'Logger.ts','function':'emit'}, {'id':4,'kind':'log_effect','file_path':'Caller.ts','function':'call'}])
        self.assertEqual(['code_log_statement','code_log_effect'],[a['record_type'] for a in raw])
        self.assertEqual([4],compact_code_anchor(raw[0])['record_ids'])
