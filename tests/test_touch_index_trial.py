import copy
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from pathlib import Path
from tools.agent_memory_runtime.query_touch_index_trial import make_touch_trial, valid_trial, capture_log_candidates

Q='请定位触摸回调和索引读取所在源码。'
MODULE='tools.agent_memory_runtime.query_touch_index_trial.trial_state'

class TouchTrialTests(unittest.TestCase):
    def test_binding_copy_mutation_and_version(self):
        p=SimpleNamespace(project_id='p',root=Path('/tmp/project')); baseline={'query':Q,'project_id':'p','project_path':'/tmp/project'}; trial={**baseline,'value':1}; pool=[{'id':1}]
        empty=capture_log_candidates(p,Q,Q,[],[])
        with patch(MODULE,return_value='state1'):
            x=make_touch_trial(p,Q,baseline,trial,pool,'state1',empty,empty)
            self.assertTrue(valid_trial(p,Q,x))
            self.assertFalse(valid_trial(p,Q,copy.copy(x)))
            self.assertFalse(valid_trial(p,Q,copy.deepcopy(x)))
            self.assertFalse(valid_trial(p,Q+'x',x))
            pool[0]['id']=2
            self.assertTrue(valid_trial(p,Q,x))
            x._pool[0]['id']=3
            self.assertFalse(valid_trial(p,Q,x))
            x=make_touch_trial(p,Q,baseline,trial,[],'state1',empty,empty)
            x['value']=2
            self.assertFalse(valid_trial(p,Q,x))
        with patch(MODULE,return_value='state2'):
            self.assertIsNone(make_touch_trial(p,Q,baseline,trial,[],'state1',empty,empty))
            self.assertFalse(valid_trial(p,Q,x))

    def test_bad_state_request_and_pool(self):
        with patch(MODULE,return_value='state1'):
            for query,pool,state in [(Q,[],None),(Q,{},'state1'),('no',[],'state1')]:
                self.assertIsNone(make_touch_trial(object(),query,{}, {},pool,state))


    def test_private_candidates_complete_snapshot_and_issuer(self):
        from tools.agent_memory_runtime.query_touch_index_trial import capture_log_candidates, log_candidate_rows
        p=SimpleNamespace(project_id='p',root=Path('/tmp/project'))
        direct=[{'id':1,'project_id':'p','message_template':'unscored','extra':'keep'}]
        effects=[{'id':2,'project_id':'p','sink_log_id':1,'evidence_class':'inferred_wrapped'}]
        cap=capture_log_candidates(p,Q,Q,direct,effects)
        self.assertEqual(log_candidate_rows(p,Q,cap),{'direct':direct,'effects':effects})
        direct[0]['extra']='changed';self.assertEqual(log_candidate_rows(p,Q,cap)['direct'][0]['extra'],'keep')
        for bad in (copy.copy(cap),copy.deepcopy(cap),{'direct':direct,'effects':effects}):self.assertIsNone(log_candidate_rows(p,Q,bad))
        self.assertIsNone(log_candidate_rows(p,Q+'x',cap))
        self.assertIsNone(log_candidate_rows(SimpleNamespace(project_id='other',root=p.root),Q,cap))
        self.assertIsNone(log_candidate_rows(p,Q,capture_log_candidates(p,Q,'wrong',[],[])))

    def test_both_candidate_sets_bound_and_not_public(self):
        from tools.agent_memory_runtime.query_touch_index_trial import capture_log_candidates
        p=SimpleNamespace(project_id='p',root=Path('/tmp/project'));base={'query':Q,'project_id':'p','project_path':'/tmp/project'}
        a=capture_log_candidates(p,Q,Q,[{'id':1}],[]);b=capture_log_candidates(p,Q,Q,[],[{'id':2}])
        with patch(MODULE,return_value='state1'):
            trial=make_touch_trial(p,Q,base,base,[],'state1',a,b)
            self.assertTrue(valid_trial(p,Q,trial));self.assertEqual(dict(trial),base)
            trial._baseline_logs=b;self.assertFalse(valid_trial(p,Q,trial))
            trial=make_touch_trial(p,Q,base,base,[],'state1',a,b)
            trial._trial_logs=None;self.assertFalse(valid_trial(p,Q,trial))
            self.assertIsNone(make_touch_trial(p,Q,base,base,[],'state1',copy.copy(a),b))

    def test_capture_keeps_legacy_pool_list_interface(self):
        from tools.agent_memory_runtime.query_touch_index_trial import capture_touch_pass,PassCaptures,capture_log_candidates
        p=SimpleNamespace(project_id='p',root=Path('/tmp/project'));cap=capture_log_candidates(p,Q,Q,[],[])
        collection=SimpleNamespace(_private_log_capture=cap);pool=[{'id':1}]
        for output in ([],PassCaptures()):
            capture_touch_pass(collection,pool,output)
            self.assertEqual(output[0],pool);self.assertIs(type(output[0]),list)
            pool[0]['id']=2;self.assertEqual(output[0][0]['id'],1);pool[0]['id']=1
            if isinstance(output,PassCaptures):self.assertIs(output.logs[0],cap)

    def test_missing_capture_is_not_empty_authority(self):
        p=SimpleNamespace(project_id='p',root=Path('/tmp/project'));base={'query':Q,'project_id':'p','project_path':'/tmp/project'}
        with patch(MODULE,return_value='state1'):self.assertIsNone(make_touch_trial(p,Q,base,base,[],'state1'))

    def test_replacement_and_reused_issuer_cannot_hide_candidates(self):
        from dataclasses import replace
        from tools.agent_memory_runtime.query_touch_index_trial import LogCandidates, log_candidate_rows
        p=SimpleNamespace(project_id='p',root=Path('/tmp/project'))
        base={'query':Q,'project_id':'p','project_path':'/tmp/project'}
        cap=capture_log_candidates(p,Q,Q,[{'id':1}], [{'id':2,'unscored':True}])
        forged=[replace(cap,effects=()), replace(cap,direct=()), replace(cap),
                LogCandidates(cap.project_id,cap.root,cap.query,cap.retrieval,
                              cap.direct,(),cap.issuer)]
        with patch(MODULE,return_value='state1'):
            for bad in forged:
                self.assertIsNone(log_candidate_rows(p,Q,bad))
                self.assertIsNone(make_touch_trial(p,Q,base,base,[],'state1',cap,bad))
                self.assertIsNone(make_touch_trial(p,Q,base,base,[],'state1',bad,cap))
            self.assertTrue(valid_trial(p,Q,make_touch_trial(p,Q,base,base,[],'state1',cap,cap)))

    def test_in_place_bypass_of_frozen_fields_invalidates_issuance(self):
        from tools.agent_memory_runtime.query_touch_index_trial import log_candidate_rows
        p=SimpleNamespace(project_id='p',root=Path('/tmp/project'))
        base={'query':Q,'project_id':'p','project_path':'/tmp/project'}
        cap=capture_log_candidates(p,Q,Q,[],[{'id':2,'unscored':True}])
        with patch(MODULE,return_value='state1'):
            trial=make_touch_trial(p,Q,base,base,[],'state1',cap,cap)
            object.__setattr__(cap,'effects',())
            self.assertIsNone(log_candidate_rows(p,Q,cap))
            self.assertFalse(valid_trial(p,Q,trial))
            self.assertIsNone(make_touch_trial(p,Q,base,base,[],'state1',cap,cap))


class UnsupportedCaptureTests(unittest.TestCase):
    def test_unsupported_request_never_iterates_candidate_rows(self):
        def unexpected():
            raise AssertionError('unsupported query serialized logs')
            yield
        self.assertIsNone(capture_log_candidates(None,'ordinary unrelated request','x',unexpected(),unexpected()))
