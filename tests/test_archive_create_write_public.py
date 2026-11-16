"""All sixteen unchanged synthetic queries through actual CLI, without stored outputs."""
import json
import tempfile
import unittest
from pathlib import Path
from tests.archive_create_write_test_support import (
    fixture,prepare,cli,ordinary_context,snapshot_database,restore_database)
from tools.agent_memory_runtime.context_record_loop_transaction import restore_whitelist


class ArchivePublicTests(unittest.TestCase):
    def test_fixed_requests_and_atomic_code_view(self):
        data=fixture(); count=0; eligible=0
        for cohort,description in data['cohorts'].items():
            with tempfile.TemporaryDirectory() as directory:
                project=prepare(Path(directory),cohort)
                saved=snapshot_database(project)
                self.addCleanup(saved.close)
                for case in [c for c in data['cases'] if c['cohort']==cohort]:
                    with self.subTest(case=case['id']):
                        restore_database(project,saved)
                        ordinary_raw,ordinary_compact,pool=ordinary_context(project,case['query'])
                        restore_database(project,saved)
                        raw=json.loads(cli(project,'context','--query',case['query'],'--json'))
                        restore_database(project,saved)
                        compact=json.loads(cli(project,'context','--query',case['query'],'--compact','--json'))
                        self.assertEqual(raw,ordinary_raw)
                        self.assertLessEqual(compact['output_budget']['estimated_tokens'],1500)
                        if case['proposed_authority']:
                            eligible+=1
                            expected=description['positive_methods']
                            anchors=compact['query_handoff']['code_anchors']
                            self.assertEqual({(a['file_path'],a['symbol']) for a in anchors},
                                             {(m['path'],m['method']) for m in expected})
                            self.assertEqual(len(anchors),len(expected))
                            for method in expected:
                                anchor=next(a for a in anchors if a['file_path']==method['path'] and a['symbol']==method['method'])
                                self.assertEqual(anchor['source_ranges'],[dict(symbol=method['method'],start_line=method['start_line'],end_line=method['end_line'])])
                                self.assertEqual(anchor['read_window'],dict(start_line=method['start_line'],end_line=method['end_line']))
                                self.assertEqual(len(anchor['source_excerpts']),1)
                                excerpt=anchor['source_excerpts'][0]
                                self.assertFalse(excerpt['truncated'])
                                self.assertEqual((excerpt['start_line'],excerpt['end_line']),(method['start_line'],method['end_line']))
                                self.assertEqual(excerpt['content'],'\n'.join(description['sources'][method['path']].splitlines()[method['start_line']-1:method['end_line']]))
                                self.assertTrue(any(r.get('kind')=='symbol' and r.get('file_path')==method['path'] and r.get('symbol')==method['method'] for r in pool))
                            self.assertEqual(restore_whitelist(compact,ordinary_compact),ordinary_compact)
                        else:
                            self.assertEqual(compact,ordinary_compact)
                        count+=1
        self.assertEqual((count,eligible),(16,4))

if __name__=='__main__':unittest.main()
