# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Private finite-source selection over an unchanged public fallback context."""
from copy import deepcopy
import hashlib,json
from pathlib import Path
from .storage import connect
from .query_render_recall import parse_render_request
from .query_language import excluded_code_candidate
from .query_ui_pair import valid_row


def snapshot(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False)

class RenderContext(dict):
    def __copy__(self):
        return dict(self)
    def __deepcopy__(self,memo):
        return deepcopy(dict(self),memo)


class RenderTrial(dict):
    def __copy__(self):
        return dict(self)
    def __deepcopy__(self,memo):
        return deepcopy(dict(self),memo)


def retain_background_candidates(query,context,items):
    request = parse_render_request(query)
    if request is None or request.capability != 'background':
        return context
    paths = {r.get('file_path') for r in items if r.get('kind') == 'symbol'
             and 'backgroundcolor' in (r.get('method_evidence') or '').split()}
    if not paths or len(paths) > 12:
        return context
    pool = deepcopy([r for r in items if r.get('file_path') in paths])
    result = RenderTrial(context); result._pool = pool
    result._binding = (query, snapshot(context), snapshot(pool))
    return result


def background_candidates(query,trial):
    if not isinstance(trial, RenderTrial):
        return None
    try:
        if trial._binding == (query, snapshot(dict(trial)), snapshot(trial._pool)):
            return trial._pool
    except (AttributeError, TypeError, ValueError):
        pass
    return None


def bind_render_context(project,query,baseline,trial):
    from .query_render_source import parse_render_source
    request = parse_render_request(query)
    if request is None:
        return baseline
    if request.capability == "background":
        from .query_background_source import parse_background_source
        parse_render_source = parse_background_source
    for context in (baseline,trial):
        h=context.get('query_handoff')or{}
        path=h.get('path_context')or{}
        anchors=h.get('code_anchors')or[]
        if (path.get('activated') or path.get('wrapped_log_evidence') or h.get('log_anchors')
                or any(a.get('graph_neighbor') or a.get('graph_relation') or a.get('log_identity_match')
                       or a.get('identity_match') for a in anchors)):
            return baseline
    pool = trial.get('wiki_matches') or []
    if request.capability == 'background':
        pool = background_candidates(query, trial)
        if pool is None:
            return baseline
    paths=sorted({r.get('file_path')for r in pool if isinstance(r.get('file_path'),str)})
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
            if not file.is_relative_to(root) or file.suffix!='.ets' or file.stat().st_size>2*1024*1024:
                continue
            raw=file.read_bytes()
            if len(raw)>2*1024*1024:
                continue
            source=raw.decode('utf-8');parsed=parse_render_source(source)
        except (OSError,UnicodeError):
            continue
        if parsed is None:
            continue
        digest=hashlib.sha256(raw).hexdigest();local=[r for r in rows if r['file_path']==name]
        owners=[r for r in local if r['symbol']==parsed['owner'] and r['symbol_type']in {'struct','component'}]
        if len(owners)!=1:
            return baseline
        owner=owners[0];f=files.get(name)or{}
        if (not valid_row(owner,project) or owner['source_digest']!=digest or f.get('source_digest')!=digest
                or f.get('index_generation')!=owner['index_generation']):
            return baseline
        if excluded_code_candidate(query,owner):
            continue
        members=[]
        spans = [('build', parsed['build_start'], parsed['build_end'])]
        if request.capability == 'cleanup':
            spans.append((parsed['helper'], parsed['helper_start'], parsed['helper_end']))
        for method,start,end in spans:
            matching=[r for r in local if r['symbol']==method and r['qualified_name']==owner['symbol']+'.'+method
                      and r['owner_name']==owner['symbol'] and r['owner_kind']=='component'
                      and r['symbol_type']in {'method','function'} and r['start_line']==start and r['end_line']==end]
            if len(matching)!=1:
                return baseline
            row=matching[0]
            if (not valid_row(row,project) or row['source_digest']!=digest
                    or row['index_generation']!=owner['index_generation']
                    or not owner['start_line']<=start<=end<=owner['end_line']):
                return baseline
            if request.capability == 'background' and not any(
                    x.get('kind') == 'symbol' and all(x.get(k) == row[k] for k in
                    ('id', 'symbol_key', 'file_path', 'source_digest', 'index_generation')) for x in pool):
                return baseline
            members.append(row)
        selected.extend(dict(source='wiki',record_id=r['id'],record_type='code_symbol',file_path=name,
            symbol=r['symbol'],symbol_type=r['symbol_type'],start_line=r['start_line'],end_line=r['end_line'])for r in members)
        receipts.append((name,digest,tuple(source.splitlines()),tuple((r['symbol'],r['start_line'],r['end_line'])for r in members)))
    if not receipts or len(receipts)>3:
        return baseline
    view=deepcopy(dict(trial));view['query_handoff']['code_anchors']=selected
    if request.capability == 'background':
        ids = {a['record_id'] for a in selected}
        view['wiki_matches'] = deepcopy([r for r in pool if r.get('kind') == 'symbol' and r.get('id') in ids])
    view['query_handoff']['callable_evidence']={'schema_version':'agent-callable-evidence/v1','certainty':'uncertain',
        'primary':None,'alternatives':[],'boundary':'positive_static_expression_template_not_runtime_proof'}
    from .context_compact import _compact_context
    if not complete_snapshot_projection(_compact_context(view,tuple(receipts)),tuple(receipts)):
        return baseline
    result=RenderContext(baseline);result._view=view;result._receipts=tuple(receipts)
    result._binding=(query,snapshot(dict(result)),snapshot(view),result._receipts)
    return result


def render_context_view(data):
    if not isinstance(data,RenderContext):
        return data,None
    try:
        current=(data.get('query'),snapshot(dict(data)),snapshot(data._view),data._receipts)
        if current!=data._binding or parse_render_request(data.get('query'))is None:
            return dict(data),None
        return data._view,data._receipts
    except (AttributeError,TypeError,ValueError):
        return dict(data),None


def attach_render_excerpts(payload,receipts,token_budget):
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
                    source='validated_request_snapshot',selection_reason='static_render_expression',truncated=actual_end<end))
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


def enrich_render_context(data,query,path_payload,freshness):
    """Only the trusted Facade's empty-path enrichment can transport a receipt."""
    baseline=deepcopy(dict(data))
    baseline['source_freshness']=freshness
    baseline.setdefault('query_handoff',{})['path_context']=path_payload
    view,receipts=render_context_view(data)
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
    if not complete_snapshot_projection(_compact_context(view,receipts),receipts):
        return baseline
    result=RenderContext(baseline);result._view=view;result._receipts=receipts
    result._binding=(query,snapshot(dict(result)),snapshot(view),receipts)
    return result
