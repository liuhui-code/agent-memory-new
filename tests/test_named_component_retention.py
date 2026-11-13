# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json
import tempfile
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.context_callable_focus import multiple_requested_anchors_present

ROOT=Path(__file__).resolve().parents[1]
PROTOCOL=json.loads((ROOT/'docs/evidence/cross-preview-followup/protocol.json').read_text())

class NamedComponentRetentionTests(AgentMemoryTestBase):
    def test_public_named_component_pair_is_not_narrowed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for name,source in PROTOCOL['sources'].items():(root/name).write_text(source)
            self.run_memory(root,'init');self.run_memory(root,'learn-path','--path','.')
            for case in PROTOCOL['queries']:
                h=json.loads(self.run_memory(root,'context','--query',case['query'],'--compact','--json').stdout)['query_handoff']
                self.assertTrue(set(case['required']) <= {a['file_path'] for a in h['code_anchors']},case['query'])
    def anchors(self):
        return [{'file_path':n+'.ets','symbol':n,'symbol_type':'component','start_line':2,'end_line':12} for n in ('EntryTile','CitationPanel')]
    def test_exact_positive_unique_owner_names_only(self):
        a=self.anchors()
        self.assertTrue(multiple_requested_anchors_present(a,{},'Locate EntryTile and CitationPanel source.'))
        for q in ['Locate EntryTile source, not CitationPanel.','Locate entry tiles and citation panels.','Locate EntryTileBackup and CitationPanel.','Locate EntryTile source.','EntryTile uses CitationPanel. Locate EntryTile.']:
            self.assertFalse(multiple_requested_anchors_present(a,{},q),q)
        a.append({**a[1],'file_path':'other/CitationPanel.ets'})
        self.assertFalse(multiple_requested_anchors_present(a,{},'Locate EntryTile and CitationPanel source.'))
    def test_unbounded_or_nonentity_records_do_not_authorize_retention(self):
        for key,value in [('end_line',None),('symbol_type','state')]:
            a=self.anchors();a[1][key]=value
            self.assertFalse(multiple_requested_anchors_present(a,{},'Locate EntryTile and CitationPanel source.'))
