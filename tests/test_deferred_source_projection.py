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
