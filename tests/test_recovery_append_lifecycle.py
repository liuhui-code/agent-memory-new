# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Hardened direct-helper rejection only; historical Group B positives archived."""
import copy
from pathlib import Path
import sqlite3
import tempfile
import unittest
from tools.agent_memory_runtime.models import Project
from tools.agent_memory_runtime.query_collect import CollectedMatches
from tools.agent_memory_runtime.query_language import positive_retrieval_query
from tools.agent_memory_runtime import query_recovery_append_capture as cap
from tools.agent_memory_runtime import query_recovery_append_lifecycle as life
from tools.agent_memory_runtime.context_recovery_append import append_transaction


class RecoveryAppendLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name)
        self.project=Project(root,root/'h',root/'m',root/'d',root/'v',root/'r','p','p')
        self.query='Locate the registry branch and store sync owners.'
        self.db=sqlite3.connect(':memory:');self.db.row_factory=sqlite3.Row;self.addCleanup(self.db.close)
        self.rows=list(self.db.execute('select 1 as id, "ordinary control status" as message_template'))
        self.collection=CollectedMatches({'wiki_matches':[],'code_log_matches':[]},{})
        self.raw={'project_id':'p','project_path':str(root),'query':self.query,
                  'query_handoff':{'code_anchors':[],'log_anchors':[]}}

    def test_direct_capture_with_real_sqlite_rows_is_not_origin(self):
        cap.capture(self.project,self.query,positive_retrieval_query(self.query),self.collection,self.rows,[])
        self.assertIsNone(cap.current(self.project,self.query,self.collection))
        self.assertNotIn(id(self.collection),cap._captures)

    def test_direct_pending_never_wraps_constructed_collection(self):
        result=life.pending(self.project,self.query,self.raw,[],self.collection)
        self.assertIs(result,self.raw);self.assertIsNone(life.final_entry(result))

    def test_typed_fake_manual_phase_chain_never_issues(self):
        fake=life.RecoveryAppendPending(copy.deepcopy(self.raw))
        self.assertIs(life.selected(fake),fake);self.assertIsNone(life.begin_facade(fake))
        fresh={'status':'current'};path={'activated':False,'path_candidates':[]}
        fake['source_freshness']=fresh;fake['query_handoff']['path_context']=path
        self.assertIs(life.finish_facade(fake,None,fresh,path),fake)
        self.assertIsNone(life.final_entry(fake));self.assertNotIn(id(fake),life._live)

    def test_forged_ticket_and_seal_attributes_do_not_register(self):
        fake=life.RecoveryAppendPending(copy.deepcopy(self.raw));fake._seal=cap.seal(dict(fake))
        fake._phase='final';fake._project=self.project;fake._collection=self.collection
        ticket=({'phase':'selected','seal':fake._seal},'{}')
        self.assertIs(life.finish_facade(fake,ticket,{},{}),fake)
        self.assertIsNone(life.final_entry(fake));self.assertNotIn(id(fake),life._live)

    def test_fake_copies_dict_and_subclass_do_not_issue(self):
        fake=life.RecoveryAppendPending(copy.deepcopy(self.raw))
        class Other(life.RecoveryAppendPending):pass
        for obj in (fake,dict(fake),copy.copy(fake),copy.deepcopy(fake),Other(fake)):
            with self.subTest(type=type(obj).__name__):
                self.assertIsNone(life.final_entry(obj));self.assertIsNone(life.begin_facade(obj))

    def test_direct_terminal_without_issued_marker_is_baseline(self):
        fake=life.RecoveryAppendPending(copy.deepcopy(self.raw));baseline={'unchanged':[]}
        self.assertIs(append_transaction(fake,dict(fake),baseline,object()),baseline)
        self.assertEqual(baseline,{'unchanged':[]})


if __name__=='__main__':unittest.main()
