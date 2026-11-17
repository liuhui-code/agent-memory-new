# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Draft: one real receipt, two shared transaction calls; no CLI or outer-budget claim."""
import ast
from copy import deepcopy
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import sys
import traceback

REPO=Path('/workspace/scratch/dcdb41e16594/validation13-dispatch-logs-20261117')
EVID=REPO/'docs/evidence/validation13-dispatch-logs'


def run_case(fresh_root):
    root=Path(fresh_root);root.mkdir(parents=True,exist_ok=False)
    report={'scope':'shared terminal transaction budget only','factory_calls':0,'transaction_calls':0}
    previous=sys.gettrace()
    try:
        assert previous is None
        sys.path.insert(0,str(REPO))
        spec=importlib.util.spec_from_file_location('budget_v2_factory',EVID/'validation_log_fixture_draft.py')
        factory=importlib.util.module_from_spec(spec);sys.modules[spec.name]=factory;spec.loader.exec_module(factory)
        from tools.agent_memory_runtime.query_validation_field_selection import ValidationContext,validation_field_receipt
        from tools.agent_memory_runtime.context_compact import _compact_context
        from tools.agent_memory_runtime import context_record_loop_transaction as transaction
        report['factory_calls']=1
        f=factory.make_fixture(root/'fixture','logged')
        context=f.issued_raw
        assert type(context) is ValidationContext,'requires real serving issuance'
        anchors=validation_field_receipt(context)
        assert anchors is not None,'requires genuine current receipt'
        baseline=_compact_context(dict(context))
        original=deepcopy(baseline);original_anchors=deepcopy(anchors)
        report['transaction_calls']+=1
        normal=transaction.apply_record_loop_transaction(baseline,anchors)
        assert normal is not baseline and normal['query_handoff']['code_anchors']==anchors
        assert transaction.restore_whitelist(normal,baseline)==baseline
        assert baseline==original and anchors==original_anchors
        limited=deepcopy(baseline);limited['output_budget']['target_tokens']=1
        limited_before=deepcopy(limited)
        # Locate the actual existing budget condition and its return statement.
        source=Path(transaction.__file__).read_text();tree=ast.parse(source)
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='apply_record_loop_transaction')
        conditions=[n for n in ast.walk(fn) if isinstance(n,ast.If)
                    and ast.unparse(n.test)=="estimate_payload_tokens(candidate) > min(1500, budget['target_tokens'])"]
        assert len(conditions)==1 and len(conditions[0].body)==1
        branch=conditions[0].body[0];assert isinstance(branch,ast.Return) and ast.unparse(branch.value)=='baseline'
        events=[]
        def observer(frame,event,arg):
            if frame.f_code is not transaction.apply_record_loop_transaction.__code__:return None
            if event=='line' and frame.f_lineno==branch.lineno:
                candidate=frame.f_locals['candidate'];budget=frame.f_locals['budget']
                estimate=transaction.estimate_payload_tokens(candidate);target=min(1500,budget['target_tokens'])
                events.append({'event':'budget-return-line','line':frame.f_lineno,'estimate':estimate,'limit':target})
                assert estimate>target and target==1
            if event=='return':events.append({'event':'return','line':frame.f_lineno,'same_baseline':arg is limited})
            return observer
        sys.settrace(observer)
        report['transaction_calls']+=1
        rejected=transaction.apply_record_loop_transaction(limited,anchors)
        sys.settrace(previous)
        assert rejected is limited and limited==limited_before and anchors==original_anchors
        assert len([e for e in events if e['event']=='budget-return-line'])==1
        assert events[-1]['event']=='return' and events[-1]['line']==branch.lineno and events[-1]['same_baseline']
        report.update(status='PASS_SHARED_TRANSACTION_COMPONENT_ONLY',trace=events,
                      transaction_sha256=hashlib.sha256(source.encode()).hexdigest(),
                      baseline=baseline,normal=normal,limited_before=limited_before,limited_after=limited,
                      receipt_anchors=anchors,raw=dict(context))
    except BaseException as error:
        report.update(status='FAIL',error=type(error).__name__+': '+str(error),traceback=traceback.format_exc())
        raise
    finally:
        sys.settrace(previous)
        (root/'RESULT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return report

if __name__=='__main__':raise SystemExit('DRAFT: independent freeze/approval required; no automatic execution')
