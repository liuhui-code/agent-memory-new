"""Finite positive source-set capability; raw context and log evidence stay intact."""
from copy import deepcopy
import hashlib
import re
from pathlib import Path
from .storage import connect
from .query_output_loop_selection import valid_row, snapshot
from .query_record_loop_request import record_loop_request
from .record_loop_source import parse_record_loop

FIELDS = ('id','project_id','file_path','symbol','symbol_key','qualified_name','start_line','end_line',
          'source_digest','index_generation','owner_name','owner_kind','semantic_adapter','evidence_class','symbol_type')


class RecordLoopContext(dict):
    def __copy__(self): return dict(self)
    def __deepcopy__(self,memo): return deepcopy(dict(self),memo)


def protected_record_loop(data,query,pool):
    from .log_event_identity import event_match
    from .query_log_owner_admission import independently_named_log_owner
    handoff=data.get('query_handoff');path=handoff.get('path_context',{}) if isinstance(handoff,dict) else None
    if not isinstance(path,dict): return True
    if any(path.get(k) for k in ('activated','wrapped_log_evidence','path_candidates','seeds')): return True
    for key in ('code_anchors','log_anchors'):
        if not isinstance(handoff.get(key),list): return True
        for item in handoff[key]:
            if not isinstance(item,dict): return True
            if any(item.get(k) for k in ('identity_match','log_identity_match','graph_neighbor','graph_relation')): return True
    for log in handoff['log_anchors']:
        if event_match(log,query)['priority']>0 or independently_named_log_owner(log,query): return True
    for row in pool:
        for key in ('file_path','symbol','qualified_name','owner_name'):
            value=row.get(key)
            if isinstance(value,str) and value and re.search(r'(?<![\w$])'+re.escape(value)+r'(?![\w$])',query,re.I): return True
    return False


def qualified_anchors(project,query,pool):
    mode=record_loop_request(query)
    if mode is None: return None
    file_paths={r.get('file_path')for r in pool if r.get('kind')=='file'}
    paths=sorted(file_paths & {r.get('file_path')for r in pool if r.get('kind')=='symbol'})
    if not paths or len(paths)>12:return None
    with connect(project) as conn:
        marks=','.join('?'for _ in paths);args=(project.project_id,*paths)
        rows=[dict(r)for r in conn.execute('SELECT * FROM code_symbols WHERE project_id=? AND file_path IN ('+marks+')',args)]
        files=[dict(r)for r in conn.execute('SELECT * FROM code_files WHERE project_id=? AND file_path IN ('+marks+')',args)]
    anchors=[];members=[];root=Path(project.root).resolve()
    for name in paths:
        try:
            file=(root/name).resolve()
            if not file.is_relative_to(root):return None
            if file.suffix not in {'.ts','.ets'}:continue
            with file.open('rb')as stream:raw=stream.read(2*1024*1024+1)
            if len(raw)>2*1024*1024:continue
            source=raw.decode('utf-8')
            current=[f for f in files if f['file_path']==name]
            if len(current)!=1 or current[0].get('source_digest')!=hashlib.sha256(raw).hexdigest():return None
            parsed=parse_record_loop(source,whole_class=True)
        except (OSError,UnicodeError):continue
        if parsed is None:continue
        methods=[m for m in parsed['methods'] if mode=='result' or m['update_form']=='append']
        if not methods:continue
        digest=hashlib.sha256(raw).hexdigest();local=[r for r in rows if r['file_path']==name]
        owners=[r for r in local if r['symbol_type']=='class' and r['symbol']==parsed['owner']]
        fs=[r for r in files if r['file_path']==name]
        if len(owners)!=1 or len(fs)!=1:return None
        owner=owners[0];f=fs[0]
        if (not valid_row(owner,project) or owner['qualified_name']!=parsed['owner']
            or owner.get('owner_name')not in ('',None) or not owner.get('owner_kind')
            or owner['source_digest']!=digest or f.get('source_digest')!=digest
            or f.get('index_generation')!=owner['index_generation']
            or (owner['start_line'],owner['end_line'])!=(parsed['start_line'],parsed['end_line'])):return None
        for method in methods:
            found=[r for r in local if r['symbol']==method['name'] and r['qualified_name']==parsed['owner']+'.'+method['name']
                   and r['owner_name']==parsed['owner'] and r['owner_kind']==owner['owner_kind']
                   and r['symbol_type']in {'function','method'}
                   and (r['start_line'],r['end_line'])==(method['start_line'],method['end_line'])]
            if len(found)!=1:return None
            row=found[0]
            if not valid_row(row,project) or row['source_digest']!=digest or row['index_generation']!=owner['index_generation']:return None
            for bound in (owner,row):
                aliases=[r for r in rows if r['id']==bound['id'] or r['symbol_key']==bound['symbol_key']]
                if any(any(r.get(k)!=bound.get(k)for k in FIELDS)for r in aliases):return None
            recalled=[r for r in pool if r.get('file_path')==name and (r.get('id')==row['id'] or r.get('symbol_key')==row['symbol_key'])]
            if not recalled or any(r.get('kind')!='symbol' or any(r.get(k)!=row[k]for k in FIELDS)for r in recalled):return None
            members.append(deepcopy(recalled[0]));lo=row['start_line'];hi=row['end_line']
            span=dict(symbol=row['symbol'],start_line=lo,end_line=hi)
            anchors.append(dict(file_path=name,symbol=row['symbol'],symbol_type=row['symbol_type'],record_ids=[row['id']],
                record_type='code_symbol',source_ranges=[span],read_window=dict(start_line=lo,end_line=hi),role='primary',
                source_excerpts=[dict(span,content='\n'.join(source.splitlines()[lo-1:hi]),source='validated_request_snapshot',
                                     selection_reason='complete_direct_loop_result_method',focus_line=None,truncated=False)]))
    return (anchors,members) if anchors else None


def bind_record_loop_context(project,query,baseline,pool):
    if record_loop_request(query)is None or protected_record_loop(baseline,query,pool):return baseline
    result=qualified_anchors(project,query,pool)
    if result is None:return baseline
    anchors,members=result
    context=RecordLoopContext(baseline);context._anchors=anchors;context._members=members;context._pool=deepcopy(pool)
    context._binding=(query,snapshot(dict(context)),snapshot(anchors),snapshot(members),snapshot(pool))
    return context


def record_loop_receipt(data):
    if not isinstance(data,RecordLoopContext):return None
    try:
        if (data._binding!=(data.get('query'),snapshot(dict(data)),snapshot(data._anchors),snapshot(data._members),snapshot(data._pool))
            or record_loop_request(data.get('query'))is None or protected_record_loop(data,data['query'],data._pool)):return None
        return data._anchors
    except (AttributeError,TypeError,ValueError):return None


def compact_record_loop(data,baseline):
    from .context_record_loop_transaction import apply_record_loop_transaction
    anchors=record_loop_receipt(data)
    if anchors is None or data.get('source_freshness',{}).get('status')!='current':return baseline
    return apply_record_loop_transaction(baseline,anchors)


def enrich_record_loop(data,query,path,freshness):
    baseline=deepcopy(dict(data));baseline['source_freshness']=freshness
    baseline.setdefault('query_handoff',{})['path_context']=path
    if (record_loop_receipt(data)is None or query!=data.get('query') or freshness!=data.get('source_freshness')
        or protected_record_loop(baseline,query,data._pool)):return baseline
    result=RecordLoopContext(baseline);result._anchors=deepcopy(data._anchors);result._members=deepcopy(data._members);result._pool=deepcopy(data._pool)
    result._binding=(query,snapshot(dict(result)),snapshot(result._anchors),snapshot(result._members),snapshot(result._pool))
    return result


def accounting_record_loop(data):
    from .context_compact import _compact_context
    baseline=_compact_context(dict(data));candidate=compact_record_loop(data,baseline)
    if candidate is baseline:return data
    view=deepcopy(dict(data));view['wiki_matches']=deepcopy(data._members)
    view['query_handoff']['code_anchors']=deepcopy(data._anchors)
    return view
