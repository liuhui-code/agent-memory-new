# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import argparse
from copy import deepcopy
import contextlib
import io
import unittest
from unittest.mock import patch
from tools.agent_memory_runtime import context_request_policy as p
from tools.agent_memory_runtime.context_compact import compact_context, _compact_context
from tools.agent_memory_runtime.context_callable_focus import focus_callable_anchors
from tools.agent_memory_runtime import command_handlers as handlers


class RequestPolicyTests(unittest.TestCase):
    def test_default_and_explicit_budget(self):
        raw = {'query': 'inspect', 'query_handoff': {}}
        old = deepcopy(raw)
        self.assertEqual(compact_context(raw), _compact_context(raw))
        self.assertEqual(compact_context(raw, token_budget=2000)['output_budget']['target_tokens'], 2000)
        self.assertEqual(raw, old)
        self.assertEqual(p.current(), p.Policy())

    def test_scoped_nested_exception_and_callback_identity(self):
        def dispatch(data, callback):
            self.assertIs(callback, _compact_context)
            self.assertEqual(p.current().budget, 2000)
            compact_context({'query_handoff': {}})
            self.assertEqual(p.current().budget, 2000)
            raise RuntimeError('stop')
        with self.assertRaises(RuntimeError):
            p.render({}, _compact_context, dispatch, 2000, False)
        self.assertEqual(p.current(), p.Policy())

    def test_preserve_final_fallback_and_protected_values(self):
        anchors = [{'file_path': 'a'}, {'file_path': 'b'}]
        ev = {'certainty': 'bounded', 'primary': {'file_path': 'a', 'source_range': {'start_line': 1}}}
        self.assertEqual(len(focus_callable_anchors(anchors, ev, False)), 1)
        def dispatch(data, callback):
            p.mark_ordinary()
            self.assertIs(focus_callable_anchors(anchors, ev, False), anchors)
            h = {'code_anchors': anchors, 'callable_evidence': {'unknown': ['unresolved']}, 'log_anchors': [1,2,3]}
            before = p.capture({'query_handoff':h})
            result = {'query_handoff': deepcopy(h)}
            p.finalize(result, 2000)
            self.assertIs(p.check(result, before), result)
            changed = deepcopy(result); changed['query_handoff']['callable_evidence'] = {}
            with self.assertRaises(p.CompactRequestIncomplete): p.check(changed, before)
            return result
        p.render({}, _compact_context, dispatch, 2000, True)

    def test_attachment_narrow_additions_and_overflow(self):
        def dispatch(data, callback):
            p.mark_ordinary(); before = p.capture({'query_handoff': {'code_anchors': [{'file_path': 'a'}]}})
            h = deepcopy(before['handoff']); h['code_anchors'][0]['source_excerpts'] = [{'content':'abc', 'truncated':True, 'source':'current_worktree', 'start_line':1, 'end_line':1, 'selection_reason':'anchor_range', 'symbol':'A'}]
            h['source_excerpt_policy'] = {'source':'current_worktree','body_persisted':False,'excerpt_count':1,'excerpt_chars':3}
            result = {'query_handoff':h,'output_budget':{'truncated':True}}; p.finalize(result,2000); p.check(result,before)
            self.assertTrue(result['output_budget']['truncated'])
            bad=deepcopy(result); del bad['query_handoff']['code_anchors'][0]['source_excerpts'][0]['start_line']
            with self.assertRaises(p.CompactRequestIncomplete): p.check(bad,before)
            bad=deepcopy(result); bad['source_freshness']={'changed':True}
            with self.assertRaises(p.CompactRequestIncomplete): p.check(bad,before)
            huge={'query_handoff':{'risk':'x'*10000}}
            with self.assertRaises(p.CompactRequestIncomplete): p.finalize(huge,2000)
            return result
        p.render({},_compact_context,dispatch,2000,True)

    def test_invalid_before_project_access(self):
        args = argparse.Namespace(compact=False, compact_token_budget=2000)
        with patch.object(handlers,'resolve_project') as resolve:
            with self.assertRaises(ValueError): handlers.context(args)
            resolve.assert_not_called()
        for b in (True, 0, 2001, '2000'):
            with self.assertRaises(ValueError): compact_context({},token_budget=b)

    def test_failure_does_not_write_success_records(self):
        args=argparse.Namespace(compact=True,compact_token_budget=2000,preserve_selected_source_anchors=True,project='.',memory_home=None,query='x')
        with patch.object(handlers,'resolve_project'), patch.object(handlers,'ensure_initialized'), patch.object(handlers,'build_context_facade'), patch.object(handlers,'compact_context',side_effect=p.CompactRequestIncomplete('too_big')), patch.object(handlers,'record_query_usage') as usage, patch.object(handlers,'append_query_performance_sample') as perf, contextlib.redirect_stdout(io.StringIO()) as stdout:
            with self.assertRaises(SystemExit) as exc: handlers.context(args)
            self.assertEqual(exc.exception.code,2); usage.assert_not_called(); perf.assert_not_called()
            self.assertIn('agent-context-incomplete/v1',stdout.getvalue())
