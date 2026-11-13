# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import copy,json,tempfile,unittest
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.query_callable_evidence import callable_evidence
D=Path(__file__).resolve().parents[1]/'docs/evidence/initializer-scope-current'

def localization(second_start=7, second_score=20, second_path='Twin.ts', missing=False):
    rows=[];ranges=[]
    for i,start,score,path in [(1,2,20,'Twin.ts'),(2,second_start,second_score,second_path)]:
        rows.append(dict(file_path=path,symbol='execute',owner_kind='class',owner_name='Owner'+str(i),symbol_id=i,start_line=start,end_line=start+2,score=score,evidence_score=score,reasons=['exact_symbol']))
        if not(missing and i==2):ranges.append(dict(file_path=path,symbol='execute',symbol_id=i,start_line=start,end_line=start+2,selection_reason='callable_symbol_range'))
    return dict(callable_candidates=rows,source_ranges=ranges)

class SameFileAmbiguityTests(unittest.TestCase):
    def test_same_file_distinct_ranges_are_not_erased_for_certainty(self):
        data=localization();before=copy.deepcopy(data);out=callable_evidence(data)
        self.assertEqual('uncertain',out['certainty']);self.assertEqual([],out['alternatives'])
        self.assertEqual(before,data)
    def test_existing_dominant_and_multifile_behavior(self):
        self.assertEqual('bounded',callable_evidence(localization(second_score=12))['certainty'])
        self.assertEqual('uncertain',callable_evidence(localization(second_path='Other.ts'))['certainty'])
    def test_same_range_duplicate_does_not_create_ambiguity(self):
        self.assertEqual('bounded',callable_evidence(localization(second_start=2))['certainty'])

class SameFileAmbiguityPublicTests(AgentMemoryTestBase):
    def test_unqualified_is_uncertain_but_named_owners_still_resolve(self):
        p=next(s for s in json.loads((D/'protocol.json').read_text())['scenarios'] if s['id']=='same-file-declared-owners')
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for name,source in p['sources'].items():(root/name).write_text(source)
            self.run_memory(root,'init');self.run_memory(root,'learn-path','--path','.')
            for query,expected in [('Locate execute implementation.',None),('Locate UploadHandler.execute implementation.','UploadHandler'),('Locate DiscardHandler.execute implementation.','DiscardHandler')]:
                out=json.loads(self.run_memory(root,'context','--query',query,'--json').stdout)['query_handoff']['callable_evidence']
                self.assertEqual('uncertain' if expected is None else 'bounded',out['certainty'])
                if expected:self.assertEqual(expected,out['primary']['owner_name'])
