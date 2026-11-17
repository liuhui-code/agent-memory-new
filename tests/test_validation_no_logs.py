# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Pass-local empty-lane authority includes actual hidden collector effects."""
from copy import copy,deepcopy
from dataclasses import replace,FrozenInstanceError
import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from tests.archive_create_write_test_support import cli
from tools.agent_memory_runtime.storage import resolve_project,connect
from tools.agent_memory_runtime.query_collect import collect_matches_with_audit,CollectedMatches
from tools.agent_memory_runtime.query_log_effects import normalize_effect
from tools.agent_memory_runtime.query_validation_no_logs import (
    validation_no_logs,check_validation_no_logs,capture_validation_no_logs,
)
Q='Locate the account validation-stop and dispatch source.'

class ValidationNoLogsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
        root=Path(cls.tmp.name);source=root/'source';source.mkdir()
        fixture=json.loads((Path(__file__).parent/'fixtures/validation_field_source.json').read_text())
        for name,text in fixture['sources']['account-owner-and-method'].items():(source/name).write_text(text)
        (source/'QuartzSink.ts').write_text("class QuartzSink {\n  emit(message: string): void {\n    console.info(message)\n  }\n}\n")
        (source/'QuartzWorker.ts').write_text("class QuartzWorker {\n  private sink: QuartzSink = new QuartzSink()\n  run(): void {\n    this.sink.emit('zircon')\n  }\n}\n")
        cls.project=resolve_project(str(source),str(root/'memory'));cli(cls.project,'init');cli(cls.project,'learn-path','--path','.','--json')
    def test_real_empty_positive_and_cross_pass(self):
        a=collect_matches_with_audit(self.project,Q);b=collect_matches_with_audit(self.project,Q)
        cap=validation_no_logs(self.project,Q,a);self.assertIsNotNone(cap)
        self.assertEqual(a.recall_audit['tables']['code_log_statements']['candidate_count'],0)
        self.assertEqual(a.matches['code_log_matches'],[])
        self.assertTrue(check_validation_no_logs(self.project,Q,a,cap))
        self.assertFalse(check_validation_no_logs(self.project,Q,b,cap))
    def test_actual_collector_hidden_effect_denies_capture(self):
        with connect(self.project)as db:
            row=db.execute("SELECT * FROM code_log_effects WHERE file_path='QuartzWorker.ts'").fetchone()
            self.assertIsNotNone(row);effect=normalize_effect(row)
        with patch('tools.agent_memory_runtime.query_collect.collect_log_effect_matches',return_value=[effect])as actual:
            collection=collect_matches_with_audit(self.project,Q)
        actual.assert_called_once()
        self.assertEqual(collection.recall_audit['tables']['code_log_statements']['candidate_count'],0)
        self.assertEqual(collection.matches['code_log_matches'],[])
        self.assertIsNone(validation_no_logs(self.project,Q,collection))
    def test_copy_replace_wrong_types_and_missing_are_unissued(self):
        collection=collect_matches_with_audit(self.project,Q);cap=validation_no_logs(self.project,Q,collection);self.assertIsNotNone(cap)
        for obj in (None,{},object(),copy(collection),deepcopy(collection),replace(collection),CollectedMatches(collection.matches,collection.recall_audit)):
            self.assertIsNone(validation_no_logs(self.project,Q,obj))
        for forged in (copy(cap),deepcopy(cap),replace(cap)):
            self.assertFalse(check_validation_no_logs(self.project,Q,collection,forged))
    def test_frozen_capture_and_object_setattr_tamper_detected(self):
        collection=collect_matches_with_audit(self.project,Q);cap=validation_no_logs(self.project,Q,collection)
        with self.assertRaises(FrozenInstanceError):cap.query='changed'
        old=cap.query;object.__setattr__(cap,'query','changed')
        try:self.assertIsNone(validation_no_logs(self.project,Q,collection))
        finally:object.__setattr__(cap,'query',old)
        self.assertIs(validation_no_logs(self.project,Q,collection),cap)
    def test_cross_query_project_root_and_database(self):
        collection=collect_matches_with_audit(self.project,Q)
        self.assertIsNone(validation_no_logs(self.project,'Locate the purchase validation-stop and dispatch source.',collection))
        for field,value in [('project_id','different'),('root',self.project.root/'different'),('db_path',self.project.db_path.with_name('other.db'))]:
            args={k:getattr(self.project,k)for k in ('project_id','root','db_path')};args[field]=value
            self.assertIsNone(validation_no_logs(SimpleNamespace(**args),Q,collection),field)
    def test_nonvalidation_does_not_iterate_or_touch_project(self):
        class Bomb:
            def __iter__(self):raise AssertionError('iterated unsupported input')
            def __getattribute__(self,name):raise AssertionError('touched unsupported project')
        capture_validation_no_logs(Bomb(),'unsupported','unsupported',Bomb(),Bomb(),Bomb())
        self.assertIsNone(validation_no_logs(Bomb(),'unsupported',Bomb()))
    def test_wrong_lane_types_do_not_issue(self):
        for direct,effects in ((None,[]),([],None),((),[]),([],()),([{}],[]),([],[{}])):
            collection=CollectedMatches({'code_log_matches':[]},{});capture_validation_no_logs(self.project,Q,Q,collection,direct,effects)
            self.assertIsNone(validation_no_logs(self.project,Q,collection))
    def test_nonempty_recapture_revokes_old_empty_pass(self):
        collection=collect_matches_with_audit(self.project,Q)
        old=validation_no_logs(self.project,Q,collection);self.assertIsNotNone(old)
        capture_validation_no_logs(self.project,Q,Q,collection,[],[{'kind':'log_effect'}])
        self.assertIsNone(validation_no_logs(self.project,Q,collection))
        self.assertFalse(check_validation_no_logs(self.project,Q,collection,old))
    def test_later_visible_log_mutation_invalidates_capture(self):
        collection=collect_matches_with_audit(self.project,Q)
        self.assertIsNotNone(validation_no_logs(self.project,Q,collection))
        collection.matches['code_log_matches'].append({'kind':'log_effect'})
        self.assertIsNone(validation_no_logs(self.project,Q,collection))
