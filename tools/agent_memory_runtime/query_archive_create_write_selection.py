"""Finite positive source-set capability; raw context and log evidence stay intact."""
from copy import deepcopy
import hashlib
from pathlib import Path
from .storage import connect
from .query_output_loop_selection import valid_row, snapshot
from .query_archive_create_write_request import archive_create_write_request
from .archive_create_write_source import parse_archive_create_write

from .query_record_loop_selection import FIELDS, protected_record_loop as protected_archive_create_write


class ArchiveCreateWriteContext(dict):
    def __copy__(self): return dict(self)
    def __deepcopy__(self,memo): return deepcopy(dict(self),memo)


def qualified_anchors(project,query,pool):
    mode=archive_create_write_request(query)
    if mode is None: return None
    file_paths={r.get('file_path')for r in pool if r.get('kind')=='file'}
    if any(not isinstance(p,str) or not p for p in file_paths):return None
    # Inspect recalled files, but never admit a method missing from that same pool.
    # Intersecting with symbol paths silently hid a positive whose row was absent.
    paths=sorted(file_paths)
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
            if len(raw)>2*1024*1024:return None
            source=raw.decode('utf-8')
            current=[f for f in files if f['file_path']==name]
            if len(current)!=1 or current[0].get('source_digest')!=hashlib.sha256(raw).hexdigest():return None
            parsed=parse_archive_create_write(source)
        except (OSError,UnicodeError):return None
        if parsed is None:continue
        methods=parsed['methods']
        if not methods:continue
        digest=hashlib.sha256(raw).hexdigest();local=[r for r in rows if r['file_path']==name]
        owners=[r for r in local if r['symbol_type']=='class' and r['symbol']==parsed['owner']]
        fs=[r for r in files if r['file_path']==name]
        if len(owners)!=1 or len(fs)!=1:return None
        owner=owners[0];f=fs[0]
        file_fields=('id','project_id','file_path','language','source_digest','index_generation')
        recalled_files=[r for r in pool if r.get('kind')=='file' and (r.get('file_path')==name or r.get('id')==f['id'])]
        if (not recalled_files or type(f.get('id'))is not int or f['id']<=0
            or f.get('project_id')!=project.project_id
            or any(any(r.get(k)!=f.get(k)for k in file_fields)for r in recalled_files)):
            return None
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
                pool_aliases=[r for r in pool if r.get('kind')=='symbol' and (r.get('id')==bound['id'] or r.get('symbol_key')==bound['symbol_key'])]
                if any(any(r.get(k)!=bound.get(k)for k in FIELDS)for r in pool_aliases):return None
            recalled=[r for r in pool if r.get('file_path')==name and (r.get('id')==row['id'] or r.get('symbol_key')==row['symbol_key'])]
            if not recalled or any(r.get('kind')!='symbol' or any(r.get(k)!=row[k]for k in FIELDS)for r in recalled):return None
            members.append(deepcopy(recalled[0]));lo=row['start_line'];hi=row['end_line']
            span=dict(symbol=row['symbol'],start_line=lo,end_line=hi)
            anchors.append(dict(file_path=name,symbol=row['symbol'],symbol_type=row['symbol_type'],record_ids=[row['id']],
                record_type='code_symbol',source_ranges=[span],read_window=dict(start_line=lo,end_line=hi),role='primary',
                source_excerpts=[dict(span,content='\n'.join(source.splitlines()[lo-1:hi]),source='validated_request_snapshot',
                                     selection_reason='static_create_same_fd_write_same_path_call',focus_line=None,truncated=False)]))
    return (anchors,members) if anchors else None


def bind_archive_create_write_context(project,query,baseline,pool):
    if type(pool)is not list or any(type(r)is not dict for r in pool):return baseline
    if archive_create_write_request(query)is None or protected_archive_create_write(baseline,query,pool,pending=True):return baseline
    result=qualified_anchors(project,query,pool)
    if result is None:return baseline
    anchors,members=result
    context=ArchiveCreateWriteContext(baseline);context._anchors=anchors;context._members=members;context._pool=deepcopy(pool)
    context._root=Path(project.root).resolve()
    context._binding=(query,snapshot(dict(context)),snapshot(anchors),snapshot(members),snapshot(pool),str(context._root))
    return context


def archive_create_write_receipt(data, *, pending=False):
    if not isinstance(data,ArchiveCreateWriteContext):return None
    try:
        if (data._binding!=(data.get('query'),snapshot(dict(data)),snapshot(data._anchors),snapshot(data._members),snapshot(data._pool),str(data._root))
            or archive_create_write_request(data.get('query'))is None or protected_archive_create_write(data,data['query'],data._pool,pending=pending)):return None
        for name,digest in {(r['file_path'],r['source_digest'])for r in data._members}:
            file=(data._root/name).resolve()
            if not file.is_relative_to(data._root):return None
            with file.open('rb')as stream:raw=stream.read(2*1024*1024+1)
            if hashlib.sha256(raw).hexdigest()!=digest:return None
        return data._anchors
    except (AttributeError,TypeError,ValueError,OSError):return None


def compact_archive_create_write(data,baseline):
    from .context_record_loop_transaction import apply_record_loop_transaction
    anchors=archive_create_write_receipt(data)
    freshness=data.get('source_freshness',{})
    if (anchors is None or freshness.get('status')!='current'
        or any(r['index_generation']!=freshness.get('generation')for r in data._members)):return baseline
    return apply_record_loop_transaction(baseline,anchors)


def enrich_archive_create_write(data,query,path,freshness):
    baseline=deepcopy(dict(data));baseline['source_freshness']=freshness
    baseline.setdefault('query_handoff',{})['path_context']=path
    if (archive_create_write_receipt(data,pending=True)is None or query!=data.get('query') or freshness!=data.get('source_freshness')
        or protected_archive_create_write(baseline,query,data._pool)):return baseline
    result=ArchiveCreateWriteContext(baseline);result._anchors=deepcopy(data._anchors);result._members=deepcopy(data._members);result._pool=deepcopy(data._pool)
    result._root=data._root
    result._binding=(query,snapshot(dict(result)),snapshot(result._anchors),snapshot(result._members),snapshot(result._pool),str(result._root))
    return result


def accounting_archive_create_write(data):
    from .context_compact import _compact_context
    baseline=_compact_context(dict(data));candidate=compact_archive_create_write(data,baseline)
    if candidate is baseline:return data
    view=deepcopy(dict(data));view['wiki_matches']=deepcopy(data._members)
    view['query_handoff']['code_anchors']=deepcopy(data._anchors)
    return view
