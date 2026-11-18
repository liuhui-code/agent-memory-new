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

    def test_completion_scope_does_not_require_causality_for_location(self):
        entry=(ROOT/'skills/agent-memory-query/SKILL.md').read_text()
        body=(ROOT/'skills/agent-memory-query/references/code-understanding.md').read_text()
        self.assertIn('3. For diagnosis, stop only when an inspected causal file',entry)
        self.assertIn('For diagnosis, before `supported_cause_found`',entry)
        self.assertIn('For diagnosis, the local Agent CLI must summarize',entry)
        for marker in ['every requested, verifiable source fact','no direct contradiction','unverified remainder or budget stop','callback attachment without its return','log string alone does not complete','separate design protocol','not new Runtime stop enums']:
            self.assertIn(marker,body)
