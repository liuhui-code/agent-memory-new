# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Unexecuted real-wiring private authority controls; no manual issue or CLI."""
import copy
import json
from pathlib import Path
import sys
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[2]));sys.path.insert(0,str(HERE))
from validation_log_fixture_draft import make_fixture


def observe_fixture(folder,variant):
    from tools.agent_memory_runtime import query_validation_log_capture as logs
    from tools.agent_memory_runtime import query_validation_no_logs as old
    newer=[];older=[]
    new_call=logs.capture_validation_logs;old_call=old.capture_validation_no_logs
    def record(out,fn):
        def wrapper(project,query,retrieval,collection,direct,effects):
            # Detach bounded actual fixture values for observation only, not
            # authority. Preserve collection/object references for identity.
            out.append({'project':project,'query':query,'retrieval':retrieval,'collection':collection,
                        'direct':[dict(x) for x in direct],'effects':copy.deepcopy(effects)})
            return fn(project,query,retrieval,collection,direct,effects)
        return wrapper
    with patch.object(logs,'capture_validation_logs',side_effect=record(newer,new_call)), \
         patch.object(old,'capture_validation_no_logs',side_effect=record(older,old_call)):
        f=make_fixture(folder,variant)
    assert len(older)==1
    assert older[0]['collection'] is f.collection
    assert older[0]['direct']==[dict(x) for x in f.direct] and older[0]['effects']==f.effects
    if variant=='logged':
        assert len(newer)==1,'actual new capture must run exactly once, not manual test issuance'
        assert newer[0]['collection'] is older[0]['collection'] is f.collection
        for key in ('query','retrieval','direct','effects'):
            assert newer[0][key]==older[0][key],key
        assert newer[0]['project'] is older[0]['project']
    else:
        assert newer==[],'empty lane must not invoke new log capture'
        assert older[0]['direct']==older[0]['effects']==[]
    return f,{'old_calls':len(older),'new_calls':len(newer),'same_collection':True}


def assert_method_coverage(f,payload):
    targets=[('AccountDraftPanel.ts',3,9),('MemberDraftPanel.ts',3,9)]
    for path,lo,hi in targets:
        lines=f.sources[path].splitlines();matches=[]
        for anchor in payload['query_handoff']['code_anchors']:
            if anchor.get('file_path')!=path:continue
            for excerpt in anchor.get('source_excerpts',[]):
                start,end=excerpt.get('start_line'),excerpt.get('end_line')
                if (type(start)is int and type(end)is int and 1<=start<=lo<=hi<=end<=len(lines)
                    and excerpt.get('content')=='\n'.join(lines[start-1:end]) and not excerpt.get('truncated')):
                    matches.append(excerpt)
        assert matches,('missing unchanged complete method',path,lo,hi)


def run_private_case(case_id,fresh_folder):
    from tools.agent_memory_runtime.query_validation_field_selection import (
        ValidationContext,validation_field_receipt,compact_validation_field)
    from tools.agent_memory_runtime.context_compact import _compact_context
    from tools.agent_memory_runtime.query_validation_field_request import validation_field_request
    from tools.agent_memory_runtime.query_validation_binding_resources import bounded_binding_parts
    from tools.agent_memory_runtime.query_validation_log_capture import validation_logs
    from tools.agent_memory_runtime.query_validation_no_logs import validation_no_logs
    plan=json.loads((HERE/'PRIVATE-TAMPER-CONTROLS-DRAFT.json').read_text())
    assert case_id in plan['cases']
    f,calls=observe_fixture(fresh_folder,'empty' if case_id in ('empty-old-lane','empty-add-log-fields') else 'logged')
    context=f.issued_raw
    if type(context) is not ValidationContext:
        raise NotImplementedError('real wiring did not issue ValidationContext; no manual replacement allowed')
    assert validation_field_receipt(context) is not None,'genuine before-mutation receipt required'
    initial_baseline=_compact_context(dict(context))
    initial=compact_validation_field(context,initial_baseline)
    assert_method_coverage(f,initial)
    if case_id=='empty-old-lane':
        assert validation_no_logs(f.project,f.query,f.collection) is context._no_logs
        assert validation_logs(f.project,f.query,f.collection) is None
        return {'id':case_id,'calls':calls,'asserted':'unchanged actual NoLog lane+complete source'}
    if case_id=='empty-add-log-fields':
        # Mixed attributes must not reclassify an already issued empty lane.
        assert validation_no_logs(f.project,f.query,f.collection) is context._no_logs
        context._log_capture=object();context._log_proof='forged'
        assert validation_field_receipt(context) is None
        baseline=_compact_context(dict(context))
        assert compact_validation_field(context,baseline) is baseline
        return {'id':case_id,'calls':calls,'asserted':'issued empty lane cannot become mixed'}
    if not hasattr(context,'_log_capture') or not hasattr(context,'_log_proof'):
        raise NotImplementedError('locked private nonempty fields not implemented')
    assert validation_logs(f.project,f.query,f.collection) is context._log_capture
    if case_id=='logged-capture-once':
        return {'id':case_id,'calls':calls,'asserted':'actual capture+genuine complete view'}
    candidate=context
    if case_id=='logged-add-no-logs':
        assert not hasattr(context,'_no_logs'), 'logged lane must not predefine absence attribute'
        context._no_logs=object()
    elif case_id=='forged-files':
        assert type(context._files) is tuple and context._files
        path,digest=context._files[0];assert digest!='0'*64
        context._files=((path,'0'*64),)+context._files[1:]
    elif case_id=='forged-state':context._state='forged'
    elif case_id=='forged-proof':context._log_proof='forged'
    elif case_id=='copied-log-capture':
        original=context._log_capture;context._log_capture=copy.copy(original)
        assert context._log_capture is not original
    elif case_id=='copied-collection':
        original=context._collection;context._collection=copy.copy(original)
        assert context._collection is not original
    elif case_id=='reordered-pool':
        before=list(context._pool);context._pool=list(reversed(before))
        assert context._pool!=before
    elif case_id=='other-valid-query':
        query='Locate the customer validation-stop and dispatch source.'
        assert validation_field_request(query)=={'kind':'domain','value':'customer'}
        assert query!=context['query'];context['query']=query
    elif case_id=='shallow-copy':candidate=copy.copy(context)
    elif case_id=='deep-copy':candidate=copy.deepcopy(context)
    elif case_id=='json-dict':candidate=json.loads(json.dumps(dict(context)))
    else:raise AssertionError('missing fixed mutation')
    resource=None
    if case_id in ('forged-files','forged-state','forged-proof'):
        resource=bounded_binding_parts(dict(context),context._files,context._state,context._log_proof)
        assert resource is True,'must prove resource acceptance separate from authority rejection'
    assert validation_field_receipt(candidate) is None
    baseline=_compact_context(dict(candidate))
    result=compact_validation_field(candidate,baseline)
    assert result is baseline,'invalid authority must return actual baseline same object'
    return {'id':case_id,'calls':calls,'resource_only':resource,'asserted':'receipt rejected; exact baseline object'}


if __name__=='__main__':raise SystemExit('DRAFT: integration freeze required; no automatic execution')
