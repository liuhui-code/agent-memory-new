# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Finite whole-owner source qualification, not runtime lifecycle authority."""
from copy import deepcopy
import hashlib,json,re
from pathlib import Path
from .storage import connect
from .query_ui_pair import valid_row

REQUEST=re.compile(r'(?:(?:重启后恢复(?:文本|草稿|编辑内容)|(?:文本|草稿|编辑内容)保存后重启仍被清空)，)?请(?:定位|只返回)同时负责生命周期恢复、状态(?:更新|写入)和持久化的(?:源码|协调源码)。')


def lifecycle_request(query):
    return isinstance(query,str) and len(query)<=240 and REQUEST.fullmatch(query)is not None


def snapshot(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False)


def pool_identity(items):
    return tuple((x.get('kind'),x.get('id'),x.get('file_path'),x.get('symbol_key'),
                  x.get('source_digest'),x.get('index_generation')) for x in items)


class LifecycleAuthority:
    def valid(self,query,items=None):
        try:
            return (lifecycle_request(query) and self._binding==(query,self._pool,snapshot(self._receipts),self._root)
                    and (items is None or pool_identity(items)==self._pool))
        except (AttributeError,TypeError,ValueError):
            return False


class LifecycleTrial(dict):
    pass


class LifecycleContext(dict):
    def __copy__(self):
        return dict(self)
    def __deepcopy__(self,memo):
        return deepcopy(dict(self),memo)


def qualify_lifecycle(project,query,items):
    from .query_lifecycle_source import parse_lifecycle_source
    if not lifecycle_request(query):
        return None
    file_paths={x.get('file_path')for x in items if x.get('kind')=='file'}
    method_paths={x.get('file_path')for x in items if x.get('kind')=='symbol' and x.get('symbol_key')}
    paths=sorted(p for p in file_paths&method_paths if isinstance(p,str) and p)
    if not paths:
        return None
    marks=','.join('?'for _ in paths)
    with connect(project)as conn:
        args=(project.project_id,*paths)
        rows=[dict(r)for r in conn.execute(f'SELECT * FROM code_symbols WHERE project_id=? AND file_path IN ({marks})',args)]
        files={r['file_path']:dict(r)for r in conn.execute(f'SELECT * FROM code_files WHERE project_id=? AND file_path IN ({marks})',args)}
        edges=[dict(r)for r in conn.execute("SELECT * FROM memory_edges WHERE project_id=? AND source_type='code_symbol' AND target_type='code_symbol' AND relation='calls' AND valid_to IS NULL",(project.project_id,))]
    receipts=[];root=project.root.resolve()
    for path in paths:
        try:
            file=(root/path).resolve()
            if not file.is_relative_to(root) or file.suffix!='.ets' or file.stat().st_size>2*1024*1024:
                continue
            raw=file.read_bytes()
            if len(raw)>2*1024*1024:
                continue
            source=raw.decode('utf-8');parsed=parse_lifecycle_source(source)
        except(OSError,UnicodeError):
            continue
        if parsed is None:
            continue
        digest=hashlib.sha256(raw).hexdigest();local=[r for r in rows if r['file_path']==path]
        owners=[r for r in local if r['symbol_type']=='class' and r['symbol']==parsed['owner']]
        if len(owners)!=1:
            return None
        owner=owners[0];f=files.get(path)or{}
        if(not valid_row(owner,project) or owner['source_digest']!=digest or f.get('source_digest')!=digest
           or f.get('index_generation')!=owner['index_generation']
           or (owner['start_line'],owner['end_line'])!=(parsed['class_start'],parsed['class_end'])):
            return None
        members={}
        for method in parsed['methods']:
            match=[r for r in local if r['qualified_name']==owner['symbol']+'.'+method['name']
                   and r['symbol_type']in {'method','function'} and r['owner_name']==owner['symbol']
                   and (r['start_line'],r['end_line'])==(method['start_line'],method['end_line'])]
            if len(match)!=1 or not valid_row(match[0],project) or any(match[0].get(k)!=owner[k]for k in ('source_digest','index_generation')):
                return None
            members[method['name']]=match[0]
        if len(members)!=3:
            return None
        hook=members[parsed['hook']];restore=members[parsed['restore']]
        matching_edges=[]
        for edge in edges:
            if edge['source_id']!=hook['id'] or edge['target_id']!=restore['id']:
                continue
            try:e=json.loads(edge['evidence'])
            except(TypeError,ValueError):continue
            if(isinstance(e,dict) and edge.get('evidence_kind')=='static_semantic_calls'
               and e.get('schema_version')=='semantic-evidence/v1' and e.get('evidence_class')=='static'
               and e.get('source_digest')==digest and e.get('adapter')==hook['semantic_adapter']==restore['semantic_adapter']
               and edge.get('extractor_version')=='semantic-index:v1/'+hook['semantic_adapter']
               and e.get('line')==parsed['hook_call_line']):matching_edges.append(edge)
        if len(matching_edges)!=1:
            return None
        # State metadata, when present in the finite source, is independently bound.
        for field in parsed['fields']:
            if field['kind'] not in {'state','text_state'}:
                continue
            state=[r for r in local if r['symbol_type']=='state' and r['qualified_name']==owner['symbol']+'.'+field['name']]
            if(len(state)!=1 or not valid_row(state[0],project)
               or any(state[0].get(k)!=owner[k]for k in ('source_digest','index_generation'))
               or (state[0]['start_line'],state[0]['end_line'])!=(field['start_line'],field['end_line'])):
                return None
        # The current qualifying file and a method must really belong to this input pool.
        bound_file=any(x.get('kind')=='file' and x.get('file_path')==path and x.get('id')==f.get('id')
                       and x.get('source_digest')==digest and x.get('index_generation')==owner['index_generation']for x in items)
        bound_method=any(x.get('kind')=='symbol' and any(x.get('id')==m['id'] and x.get('symbol_key')==m['symbol_key']
                         and x.get('source_digest')==digest and x.get('index_generation')==owner['index_generation']for m in members.values())for x in items)
        if not bound_file or not bound_method:
            return None
        receipts.append({'path':path,'digest':digest,'source':source,'owner':owner,'members':members,
                         'parsed':parsed,'edge':matching_edges[0]})
    if not receipts or len(receipts)>3:
        return None
    result=LifecycleAuthority();result._pool=pool_identity(items);result._receipts=tuple(receipts);result._root=str(root)
    result._binding=(query,result._pool,snapshot(result._receipts),result._root)
    return result


def lifecycle_focus(authority,query,items):
    if not isinstance(authority,LifecycleAuthority) or not authority.valid(query,items):
        return None
    paths={r['path']for r in authority._receipts}
    return [x for x in items if x.get('file_path')in paths]


def protected(context):
    h=context.get('query_handoff')or{};path=h.get('path_context')or{}
    return(path.get('activated') or path.get('wrapped_log_evidence') or h.get('log_anchors')
           or any(a.get(k)for a in h.get('code_anchors')or[]for k in ('identity_match','log_identity_match','graph_neighbor','graph_relation')))


def current_sources(authority):
    try:
        root=Path(authority._root).resolve()
        for r in authority._receipts:
            file=(root/r['path']).resolve()
            if not file.is_relative_to(root) or file.stat().st_size>2*1024*1024:
                return False
            raw=file.read_bytes()
            if len(raw)>2*1024*1024 or hashlib.sha256(raw).hexdigest()!=r['digest']:
                return False
        return True
    except(OSError,AttributeError,TypeError,KeyError):return False


def bind_lifecycle_context(query,baseline,trial):
    authority=getattr(trial,'_lifecycle_authority',None)
    if(not isinstance(trial,LifecycleTrial) or not isinstance(authority,LifecycleAuthority)
       or not authority.valid(query) or not current_sources(authority) or protected(baseline) or protected(trial)):
        return baseline
    paths={r['path']for r in authority._receipts}
    if not paths<={x.get('file_path')for x in trial.get('wiki_matches')or[]}:
        return baseline
    view=deepcopy(dict(trial));anchors=[];receipts=[]
    for r in authority._receipts:
        owner=r['owner'];anchors.append(dict(source='wiki',record_type='code_symbol',record_id=owner['id'],
            file_path=r['path'],symbol=owner['symbol'],symbol_type='class',start_line=owner['start_line'],end_line=owner['end_line']))
        receipts.append((r['path'],r['digest'],tuple(r['source'].splitlines()),((owner['symbol'],owner['start_line'],owner['end_line']),)))
    view['query_handoff']['code_anchors']=anchors
    view['query_handoff']['callable_evidence']={'schema_version':'agent-callable-evidence/v1','certainty':'uncertain',
        'primary':None,'alternatives':[],'boundary':'finite_same_owner_source_shape_not_runtime_proof'}
    from .context_compact import _compact_context
    from .query_render_selection import complete_snapshot_projection
    if not complete_snapshot_projection(_compact_context(view,lifecycle_receipts=tuple(receipts)),tuple(receipts)):
        return baseline
    result=LifecycleContext(baseline);result._view=view;result._receipts=tuple(receipts);result._authority=authority
    result._binding=(query,snapshot(dict(result)),snapshot(view),result._receipts,snapshot(authority._receipts))
    return result


def lifecycle_context_view(data):
    if not isinstance(data,LifecycleContext):
        return data,None
    try:
        if(data._binding==(data.get('query'),snapshot(dict(data)),snapshot(data._view),data._receipts,snapshot(data._authority._receipts))
           and data._authority.valid(data.get('query')) and current_sources(data._authority)):
            return data._view,data._receipts
    except(AttributeError,TypeError,ValueError):pass
    return dict(data),None


def attach_lifecycle_excerpts(payload,receipts,budget):
    # Pure bounded formatter reused without reusing RenderContext authority.
    from .query_render_selection import attach_render_excerpts
    count=attach_render_excerpts(payload,receipts,budget)
    for anchor in payload['query_handoff'].get('code_anchors')or[]:
        for excerpt in anchor.get('source_excerpts')or[]:
            excerpt['selection_reason']='finite_same_owner_source_shape'
    return count


def enrich_lifecycle_context(data,query,path_payload,freshness):
    baseline=deepcopy(dict(data));baseline['source_freshness']=freshness
    baseline.setdefault('query_handoff',{})['path_context']=path_payload
    view,receipts=lifecycle_context_view(data)
    if(receipts is None or query!=data.get('query') or path_payload.get('activated')is not False
       or path_payload.get('wrapped_log_evidence') or path_payload.get('path_candidates')!=[]
       or set(path_payload)-{'schema_version','activated','activation_reason','candidate_count','seeds','path_candidates',
                            'gaps','bounds','lane_isolation','graph_revision','wrapped_log_evidence'}
       or path_payload.get('seeds') or path_payload.get('gaps') or freshness!=data.get('source_freshness')):
        return baseline
    view=deepcopy(view);view['query_handoff']['path_context']=deepcopy(path_payload)
    from .context_compact import _compact_context
    from .query_render_selection import complete_snapshot_projection
    if not complete_snapshot_projection(_compact_context(view,lifecycle_receipts=receipts),receipts):
        return baseline
    result=LifecycleContext(baseline);result._view=view;result._receipts=receipts;result._authority=data._authority
    result._binding=(query,snapshot(dict(result)),snapshot(view),receipts,snapshot(result._authority._receipts))
    return result
