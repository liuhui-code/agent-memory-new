# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Component-only terminal display. No authority to qualify source or requests."""
from copy import deepcopy
import json
from .context_record_loop_transaction import CODE_GAPS, CALLABLE_KEYS, SUFFICIENCY_KEYS, restore_whitelist
from .context_source_excerpt import MAX_EXCERPT_ANCHORS, MAX_EXCERPT_LINES, MAX_EXCERPT_CHARS, MAX_TOTAL_EXCERPT_CHARS
from .context_budget import synchronize_estimate, estimate_payload_tokens
from .context_sufficiency import diagnosis_sufficiency


def valid_component_anchors(anchors):
    if type(anchors)is not list or not 0<len(anchors)<=MAX_EXCERPT_ANCHORS:return False
    seen=set();chars=0
    for anchor in anchors:
        if type(anchor)is not dict or anchor.get('symbol_type')not in {'struct','component'}:return False
        name,path=anchor.get('symbol'),anchor.get('file_path');ids=anchor.get('record_ids')
        if not isinstance(name,str)or not name or not isinstance(path,str)or not path:return False
        if type(ids)is not list or len(ids)!=1 or type(ids[0])is not int or ids[0]<=0:return False
        if ids[0]in seen:return False
        seen.add(ids[0]);ranges=anchor.get('source_ranges');excerpts=anchor.get('source_excerpts')
        if type(ranges)is not list or len(ranges)!=1 or type(ranges[0])is not dict:return False
        span=ranges[0];lo,hi=span.get('start_line'),span.get('end_line')
        if type(lo)is not int or type(hi)is not int or not 0<lo<=hi or span.get('symbol')!=name:return False
        if anchor.get('record_type')!='code_symbol' or anchor.get('read_window')!=dict(start_line=lo,end_line=hi):return False
        if type(excerpts)is not list or len(excerpts)!=1 or type(excerpts[0])is not dict:return False
        e=excerpts[0];content=e.get('content')
        if (e.get('symbol'),e.get('start_line'),e.get('end_line'))!=(name,lo,hi):return False
        if not isinstance(content,str)or not content or e.get('truncated')is not False or e.get('source')!='validated_request_snapshot':return False
        if len(content.splitlines())!=hi-lo+1 or hi-lo+1>MAX_EXCERPT_LINES or len(content)>MAX_EXCERPT_CHARS:return False
        chars+=len(content)
    return chars<=MAX_TOTAL_EXCERPT_CHARS


def apply_command_table_transaction(baseline,anchors):
    try:
        if type(baseline)is not dict or not valid_component_anchors(anchors):return baseline
        json.dumps([baseline,anchors],allow_nan=False)
        old=baseline['query_handoff'];callable=old.get('callable_evidence');budget=baseline['output_budget']
        if type(callable)is not dict or not set(callable)<=CALLABLE_KEYS:return baseline
        if any(k in json.dumps(callable)for k in ('"log_anchors"','"path_context"','"log_identity_match"')):return baseline
        if type(budget.get('target_tokens'))is not int or budget['target_tokens']<=0 or type(budget.get('truncated'))is not bool:return baseline
        if type(baseline['evidence_gaps'])is not list or not all(isinstance(x,str)for x in baseline['evidence_gaps']):return baseline
        result=deepcopy(baseline);h=result['query_handoff'];h['code_anchors']=deepcopy(anchors)
        h['callable_evidence']={'schema_version':'agent-callable-evidence/v1','certainty':'uncertain','primary':None,'alternatives':[],
                               'boundary':'positive_direct_syntax_not_unique_owner_or_runtime_causality'}
        policy=deepcopy(h.get('source_excerpt_policy',{}))
        if type(policy)is not dict:return baseline
        policy.update(source='validated_request_snapshot',body_persisted=False,excerpt_count=len(anchors),
                      excerpt_chars=sum(len(a['source_excerpts'][0]['content'])for a in anchors));h['source_excerpt_policy']=policy
        gaps=[x for x in baseline['evidence_gaps']if x not in CODE_GAPS]
        if len({a['file_path']for a in anchors})<3:gaps.append('limited_code_anchor_diversity')
        result['evidence_gaps']=gaps;updated=diagnosis_sufficiency(h,gaps,result.get('source_freshness'))
        if any(baseline['sufficiency']['coverage'].get(k)!=updated['coverage'][k]for k in ('log_anchor_count','path_candidate_count')):return baseline
        for key in SUFFICIENCY_KEYS:result['sufficiency'][key]=updated[key]
        result['sufficiency']['coverage']['source_locatable_code_anchor']=updated['coverage']['source_locatable_code_anchor']
        synchronize_estimate(result)
        if estimate_payload_tokens(result)>min(1500,budget['target_tokens'])or restore_whitelist(result,baseline)!=baseline:return baseline
        return result
    except (KeyError,TypeError,ValueError,OverflowError):return baseline
