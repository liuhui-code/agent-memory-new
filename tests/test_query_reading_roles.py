"""Consumer-contract and real-output consistency checks, not Agent behavior eval."""
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class QueryReadingRolesTests(unittest.TestCase):
    def test_role_guidance_reachable_without_entry_growth(self):
        entry=(ROOT/'skills/agent-memory-query/SKILL.md').read_text()
        self.assertLessEqual(len(entry.splitlines()),120)
        self.assertIn('references/code-understanding.md#reading-targets-and-supporting-evidence',entry)
        body=(ROOT/'skills/agent-memory-query/references/code-understanding.md').read_text()
        for text in ['exploration priority','not ownership proof','not automatically irrelevant','two implementations','original JSON','share the original','only `semantic` and `reflection`','not Agent behavioral compliance']:
            self.assertIn(text,body)
    def test_real_source_reading_includes_log_derived_primary(self):
        d=json.loads((ROOT/'docs/releases/query-reading-roles-20261118/source-reading.json').read_text())
        anchors=d['query_handoff']['code_anchors'];callers=[a for a in anchors if a.get('source')=='wrapped_log_caller']
        self.assertEqual(len(callers),2)
        self.assertTrue(any(a.get('role')=='primary'for a in callers))
        self.assertTrue(all(a['record_type']=='code_log_effect' and a['record_ids']for a in callers))
        web=next(a for a in anchors if a['file_path'].endswith('SecureDocumentBrowser.ets'))
        source='\n'.join(e['content']for e in web['source_excerpts'])
        self.assertIn('.fileAccess(false)',source);self.assertIn('.onLoadIntercept(',source)
        self.assertNotIn('return blocked.some',source)
        self.assertTrue(any(e.get('truncated') for e in web['source_excerpts']))
    def test_explicit_log_target_can_have_wiki_provenance(self):
        d=json.loads((ROOT/'docs/releases/query-reading-roles-20261118/log-reading.json').read_text())
        self.assertIn('WRAP_PROFILE_7F19',d['query'])
        a=next(a for a in d['query_handoff']['code_anchors']if a['file_path'].endswith('WrappedProfileService.ets'))
        self.assertEqual(a['record_type'],'code_symbol')
        self.assertTrue(any('WRAP_PROFILE_7F19' in str(a)for a in d['query_handoff']['log_anchors']))
