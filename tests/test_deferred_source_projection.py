# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import copy
import json
from pathlib import Path
import unittest
from tools.agent_memory_runtime.query_code_selection import diverse_code_matches

EVIDENCE=Path(__file__).resolve().parents[1]/'docs/evidence/output-loop-followup'

class DeferredSourceProjectionTests(unittest.TestCase):
    def test_existing_public_reproduction_keeps_distinct_method(self):
        items=json.loads((EVIDENCE/'selection-stage.json').read_text())[0]['before']
        actual=diverse_code_matches(copy.deepcopy(items),5,query='Locate command output iteration and accumulation ownership when the process line reader has data.')
        self.assertIn(('PipeCollector.ts','collect'),{(r['file_path'],r['symbol']) for r in actual})
        self.assertEqual(5,len(actual))

    def records(self):
        rows=json.loads((EVIDENCE/'selection-stage.json').read_text())[0]['before']
        file=next(copy.deepcopy(r) for r in rows if r['kind']=='file' and r['file_path']=='OutputDescription.ts')
        symbol=next(copy.deepcopy(r) for r in rows if r['kind']=='symbol' and r['symbol']=='OutputDescription')
        return file,symbol

    def test_only_same_file_symbol_digest_span_and_empty_file_metadata(self):
        from tools.agent_memory_runtime.query_code_selection import same_source_projection
        file,symbol=self.records()
        self.assertTrue(same_source_projection(file,symbol))
        for key,value in [('file_path','Other.ts'),('symbol','Other'),('start_line',2),('end_line',4),('source_digest','changed'),('business_summary','Independent file responsibility'),('business_terms',['contract']),('summary','TypeScript file with 5 non-empty lines; imports important dependency')]:
            other=copy.deepcopy(file);other[key]=value
            self.assertFalse(same_source_projection(other,symbol),(key,value))
        for key in ('start_line','end_line','source_digest'):
            other=copy.deepcopy(file);other.pop(key)
            self.assertFalse(same_source_projection(other,symbol))
        self.assertFalse(same_source_projection(symbol,symbol))
        file['match_reasons'].append('graph_neighbor')
        self.assertFalse(same_source_projection(file,symbol))

    def test_file_metadata_and_all_candidates_remain_when_budget_allows(self):
        rows=json.loads((EVIDENCE/'selection-stage.json').read_text())[0]['before']
        actual=diverse_code_matches(copy.deepcopy(rows),len(rows),query='')
        self.assertEqual({(r['kind'],r['file_path'],r['symbol']) for r in rows},
                         {(r['kind'],r['file_path'],r['symbol']) for r in actual})

    def test_explicit_file_query_preserves_both_representations(self):
        file,symbol=self.records()
        actual=diverse_code_matches([file,symbol],2,query='Locate OutputDescription.ts file')
        self.assertEqual(['file','symbol'],[r['kind'] for r in actual])
        actual=diverse_code_matches([symbol,file],2,query='Locate class OutputDescription')
        self.assertEqual('symbol',actual[0]['kind'])
        self.assertEqual('class',actual[0]['symbol_type'])
