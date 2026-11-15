# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Private finite-source selection over an unchanged public fallback context."""
from copy import deepcopy
import hashlib,json,re
from pathlib import Path
from .storage import connect
from .query_command_source import command_request as parse_command_request
from .query_language import excluded_code_candidate
from .query_ui_pair import valid_row


def snapshot(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False)

class CommandContext(dict):
    def __copy__(self):
        return dict(self)
    def __deepcopy__(self,memo):
        return deepcopy(dict(self),memo)


def bind_command_context(project,query,baseline,trial):
    from .query_command_source import command_binding, declared_owner
    if parse_command_request(query) is None:
        return baseline
    for context in (baseline,trial):
        h=context.get('query_handoff')or{}
        path=h.get('path_context')or{}
        anchors=h.get('code_anchors')or[]
        if (path.get('activated') or path.get('wrapped_log_evidence') or h.get('log_anchors')
                or any(a.get('graph_neighbor') or a.get('graph_relation') or a.get('log_identity_match')
                       or a.get('identity_match') for a in anchors)):
            return baseline
    paths=sorted({r.get('file_path')for r in trial.get('wiki_matches')or[] if isinstance(r.get('file_path'),str)})
    if not paths or len(paths)>12:
        return baseline
    with connect(project)as conn:
        marks=','.join('?'for _ in paths)
        rows=[dict(r)for r in conn.execute('SELECT * FROM code_symbols WHERE project_id=? AND file_path IN ('+marks+')',[project.project_id,*paths])]
        files={r['file_path']:dict(r)for r in conn.execute('SELECT * FROM code_files WHERE project_id=? AND file_path IN ('+marks+')',[project.project_id,*paths])}
    selected=[];receipts=[];root=project.root.resolve()
    for name in paths:
        try:
            file=(root/name).resolve()
            if not file.is_relative_to(root):
                return baseline
            if file.suffix!='.ets':
                continue
            if file.stat().st_size>2*1024*1024:
                return baseline
            raw=file.read_bytes()
            if len(raw)>2*1024*1024:
                return baseline
            source=raw.decode('utf-8');parsed=command_binding(source,parse_command_request(query))
        except (OSError,UnicodeError):
            return baseline
        if parsed is None:
            from .ecma_callback_mask import callback_mask_lines
            mask=callback_mask_lines(source.splitlines())
            # Unknown lexical source or any possible array/ForEach initializer
            # is not an absence certificate. Never discard such competitors.
            if mask is None or '[' in '\n'.join(mask) or re.search(r'\bForEach\b','\n'.join(mask)):
                return baseline
            continue
        digest=hashlib.sha256(raw).hexdigest();local=[r for r in rows if r['file_path']==name]
        callback,expanded=parsed
        owners=[r for r in local if r['symbol_type']in {'struct','component'}
                and r['start_line']<=expanded['start_line']<=expanded['end_line']<=r['end_line']]
        if len(owners)!=1:
            return baseline
        owner=owners[0];f=files.get(name)or{}
        if not declared_owner(source,owner):
            return baseline
        if (not valid_row(owner,project) or owner['source_digest']!=digest or f.get('source_digest')!=digest
                or f.get('index_generation')!=owner['index_generation']):
            return baseline
        if excluded_code_candidate(query,owner):
            continue
        matching=[r for r in local if r['symbol']==callback['symbol']
                  and r['qualified_name']==owner['symbol']+'.'+callback['symbol']+'@'+str(callback['start_line'])
                  and r['owner_name']==owner['symbol'] and r['owner_kind']=='component'
                  and r['symbol_type']in {'method','function'}
                  and r['start_line']==callback['start_line'] and r['end_line']==callback['end_line']]
        if len(matching)!=1:
            return baseline
        row=matching[0]
        if (not valid_row(row,project) or row['source_digest']!=digest
                or row['index_generation']!=owner['index_generation']):
            return baseline
        # Preserve the real owner row identity and full bounded owner source.
        # Never relabel the whole initializer as the callback's indexed range.
        members=[owner]
        selected.extend(dict(source='wiki',record_id=r['id'],record_type='code_symbol',file_path=name,
            symbol=r['symbol'],symbol_type=r['symbol_type'],start_line=r['start_line'],end_line=r['end_line'])for r in members)
        receipts.append((name,digest,tuple(source.splitlines()),tuple((r['symbol'],r['start_line'],r['end_line'])for r in members)))
    if len(receipts)!=1:
        return baseline
    view=deepcopy(trial);view['query_handoff']['code_anchors']=selected
    view['query_handoff']['callable_evidence']={'schema_version':'agent-callable-evidence/v1','certainty':'uncertain',
        'primary':None,'alternatives':[],'boundary':'same_initializer_label_callback_association_not_runtime_proof'}
    from .context_compact import _compact_context
    if not complete_snapshot_projection(_compact_context(view,command_receipts=tuple(receipts)),tuple(receipts)):
        return baseline
    result=CommandContext(baseline);result._view=view;result._receipts=tuple(receipts)
    result._binding=(query,snapshot(dict(result)),snapshot(view),result._receipts)
    return result


def command_context_view(data):
    if not isinstance(data,CommandContext):
        return data,None
    try:
        current=(data.get('query'),snapshot(dict(data)),snapshot(data._view),data._receipts)
        if current!=data._binding or parse_command_request(data.get('query'))is None:
            return dict(data),None
        return data._view,data._receipts
    except (AttributeError,TypeError,ValueError):
        return dict(data),None


def attach_command_excerpts(payload,receipts,token_budget):
    from .context_source_excerpt import (MAX_EXCERPT_ANCHORS,MAX_EXCERPTS_PER_ANCHOR,MAX_EXCERPT_LINES,
        MAX_EXCERPT_CHARS,MAX_TOTAL_EXCERPT_CHARS,MIN_EXCERPT_CHARS,TOKEN_RESERVE)
    from .context_budget import estimate_payload_tokens
    remaining=min(MAX_TOTAL_EXCERPT_CHARS,max(0,token_budget-TOKEN_RESERVE-estimate_payload_tokens(payload))*3)
    if remaining<MIN_EXCERPT_CHARS:
        return 0
    count=0;used_total=0;by_path={r[0]:r for r in receipts}
    anchors=payload['query_handoff'].get('code_anchors')or[]
    for i,anchor in enumerate(anchors[:MAX_EXCERPT_ANCHORS]):
        receipt=by_path.get(anchor.get('file_path'))
        if receipt is None:
            continue
        excerpts=[];budget=min(MAX_EXCERPT_CHARS,max(MIN_EXCERPT_CHARS,remaining//max(1,len(anchors)-i)))
        for symbol,start,end in receipt[3][:MAX_EXCERPTS_PER_ANCHOR]:
            limit=min(budget,remaining);lines=[];used=0
            for line in receipt[2][start-1:min(end,start-1+MAX_EXCERPT_LINES)]:
                size=len(line)+(1 if lines else 0)
                if used+size>limit:
                    break
                lines.append(line);used+=size
            if lines:
                actual_end=start+len(lines)-1
                excerpts.append(dict(symbol=symbol,start_line=start,end_line=actual_end,content='\n'.join(lines),
                    source='validated_request_snapshot',selection_reason='static_command_binding_owner',truncated=actual_end<end))
                remaining-=used;budget-=used;used_total+=used;count+=1
            if remaining<MIN_EXCERPT_CHARS or budget<MIN_EXCERPT_CHARS:
                break
        if excerpts:
            anchor['source_excerpts']=excerpts
    if count:
        payload['query_handoff']['source_excerpt_policy']={'source':'validated_request_snapshot','body_persisted':False,
            'excerpt_count':count,'excerpt_chars':used_total}
    return count


def complete_snapshot_projection(payload,receipts):
    anchors=payload.get('query_handoff',{}).get('code_anchors')or[]
    if payload.get('output_budget',{}).get('estimated_tokens',1501)>1500:
        return False
    for path,digest,lines,members in receipts:
        excerpts=[e for a in anchors if a.get('file_path')==path for e in a.get('source_excerpts')or[]]
        for symbol,start,end in members:
            expected='\n'.join(lines[start-1:end])
            if not any(e.get('symbol')==symbol and e.get('start_line')==start and e.get('end_line')==end
                       and e.get('content')==expected and e.get('truncated') is False for e in excerpts):
                return False
    return True


def enrich_command_context(data,query,path_payload,freshness):
    """Only the trusted Facade's empty-path enrichment can transport a receipt."""
    baseline=deepcopy(dict(data))
    baseline['source_freshness']=freshness
    baseline.setdefault('query_handoff',{})['path_context']=path_payload
    view,receipts=command_context_view(data)
    if (receipts is None or query!=data.get('query')
            or path_payload.get('activated') is not False
            or path_payload.get('wrapped_log_evidence')
            or path_payload.get('path_candidates')!=[]
            or set(path_payload)-{'schema_version','activated','activation_reason','candidate_count','seeds',
                                  'path_candidates','gaps','bounds','lane_isolation','graph_revision','wrapped_log_evidence'}
            or path_payload.get('seeds') or path_payload.get('gaps')
            or freshness!=data.get('source_freshness')):
        return baseline
    view=deepcopy(view)
    view['query_handoff']['path_context']=deepcopy(path_payload)
    from .context_compact import _compact_context
    if not complete_snapshot_projection(_compact_context(view,command_receipts=receipts),receipts):
        return baseline
    result=CommandContext(baseline);result._view=view;result._receipts=receipts
    result._binding=(query,snapshot(dict(result)),snapshot(view),receipts)
    return result
