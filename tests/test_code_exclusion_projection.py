# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
from __future__ import annotations
import copy
import json
from pathlib import Path
import unittest
from tools.agent_memory_runtime.context_code_exclusions import project_code_exclusions
from tools.agent_memory_runtime.context_compact import compact_handoff

CONTROLS = json.loads(Path(__file__).with_name('code_exclusion_projection_controls.json').read_text())


def apply(row):
    item=row['input']
    return project_code_exclusions(item['code_anchors'],item['query'],item['guard_candidates'],item['raw_log_anchors'],item['path_context'])


class CodeExclusionProjectionTests(unittest.TestCase):
    def test_frozen_thirty_controls(self):
        self.assertEqual(30,len(CONTROLS))
        for row in CONTROLS:
            with self.subTest(name=row['name']):
                before=copy.deepcopy(row);result=apply(row)
                self.assertEqual(row['expected_candidate_code_anchors'],result)
                self.assertEqual(before,row)
                if row['mode']=='exact_old_fallback':self.assertIs(result,row['input']['code_anchors'])
                else:
                    self.assertLess(len(result),len(row['input']['code_anchors']))
                    self.assertTrue(all(any(item is old for old in row['input']['code_anchors']) for item in result))

    def test_post_cap_no_refill_and_log_preservation(self):
        query='Return parser implementation; exclude page.'
        paths=['src/ParserWorker.ets','src/NoisePage.ets','src/OtherWorker.ets','src/ThirdWorker.ets','src/FifthWorker.ets']
        anchors=[dict(file_path=path,symbol='run',start_line=2,end_line=5,source='wiki') for path in paths]
        logs=copy.deepcopy(CONTROLS[0]['input']['raw_log_anchors'])
        handoff={'code_anchors':anchors,'log_anchors':logs,'path_context':{'activated':False,'path_candidates':[]}}
        before=copy.deepcopy(handoff)
        result=compact_handoff(handoff,{'query':query})
        got=[x['file_path'] for x in result['code_anchors']]
        self.assertNotIn('src/NoisePage.ets',got);self.assertNotIn('src/FifthWorker.ets',got)
        self.assertEqual(['src/ParserWorker.ets','src/OtherWorker.ets','src/ThirdWorker.ets'],got)
        self.assertEqual(before,handoff)
        self.assertEqual(logs,result['log_anchors'])
