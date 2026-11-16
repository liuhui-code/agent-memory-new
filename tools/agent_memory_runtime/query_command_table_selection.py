# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Finite positive source-set capability; raw context and log evidence stay intact."""
from copy import deepcopy
import hashlib
from pathlib import Path
from .query_output_loop_selection import snapshot
from .query_command_table_request import command_table_request
from .command_table_frame_source import certify_frame
from .query_command_table_scope import metadata_frames

from .query_command_table_roles import protected_table_scope as protected_command_table


class CommandTableContext(dict):
    def __copy__(self): return dict(self)
    def __deepcopy__(self,memo): return deepcopy(dict(self),memo)



def qualified_anchors(project,query,pool):
    if not command_table_request(query):return None
    qualified=metadata_frames(project,pool)
    if qualified is None:return None
    frames=qualified['frames'];sources={};file_receipts=[];root=Path(project.root).resolve()
    for frame in frames:
        name=frame['path']
        if name in sources:continue
        try:
            file=(root/name).resolve()
            if not file.is_relative_to(root)or file.suffix!='.ets':return None
            with file.open('rb')as stream:raw=stream.read(2*1024*1024+1)
            if len(raw)>2*1024*1024:return None
            source=raw.decode('utf-8');digest=hashlib.sha256(raw).hexdigest()
        except (OSError,UnicodeError):return None
        if frame['file']['source_digest']!=digest:return None
        sources[name]=source;file_receipts.append((name,digest))
    anchors=[];members=[]
    for frame in frames:
        name=frame['path'];source=sources[name];parsed=certify_frame(source,frame)
        if parsed is False:return None
        members.extend(deepcopy(frame['members']))
        if parsed is None:continue
        owner=frame['owner'];lo,hi=owner['start_line'],owner['end_line']
        span=dict(symbol=owner['symbol'],start_line=lo,end_line=hi)
        anchors.append(dict(file_path=name,symbol=owner['symbol'],symbol_type=owner['symbol_type'],record_ids=[owner['id']],record_type='code_symbol',
            source_ranges=[span],read_window=dict(start_line=lo,end_line=hi),role='primary',source_excerpts=[dict(span,
            content='\n'.join(source.splitlines()[lo-1:hi]),source='validated_request_snapshot',selection_reason='static_ui_dispatch_table_component',focus_line=None,truncated=False)]))
    scope=dict(certification_scope='non_exhaustive_recalled_component_frames',qualified_frame_count=len(frames),
               unverified_path_count=len(set(qualified['pool_paths'])-set(sources)))
    return (anchors,members,tuple(file_receipts),scope)if anchors else None


def bind_command_table_context(project,query,baseline,pool):
    if type(pool)is not list or any(type(r)is not dict for r in pool):return baseline
    if not command_table_request(query) or protected_command_table(baseline,query,pool,pending=True):return baseline
    try:result=qualified_anchors(project,query,pool)
    except (KeyError,TypeError,ValueError,OverflowError):return baseline
    if result is None:return baseline
    anchors,members,files,scope=result
    context=CommandTableContext(baseline);context._anchors=anchors;context._members=members;context._pool=deepcopy(pool)
    context._root=Path(project.root).resolve();context._files=files;context._scope=scope
    context._binding=(query,snapshot(dict(context)),snapshot(anchors),snapshot(members),snapshot(pool),str(context._root),context._files,snapshot(context._scope))
    return context


def command_table_receipt(data, *, pending=False):
    if not isinstance(data,CommandTableContext):return None
    try:
        if (data._binding!=(data.get('query'),snapshot(dict(data)),snapshot(data._anchors),snapshot(data._members),snapshot(data._pool),str(data._root),data._files,snapshot(data._scope))
            or not command_table_request(data.get('query')) or protected_command_table(data,data['query'],data._pool,pending=pending)):return None
        for name,digest in data._files:
            file=(data._root/name).resolve()
            if not file.is_relative_to(data._root):return None
            with file.open('rb')as stream:raw=stream.read(2*1024*1024+1)
            if hashlib.sha256(raw).hexdigest()!=digest:return None
        return data._anchors
    except (AttributeError,TypeError,ValueError,OSError):return None


def compact_command_table(data,baseline):
    from .context_command_table_transaction import apply_command_table_transaction
    anchors=command_table_receipt(data)
    freshness=data.get('source_freshness',{})
    if (anchors is None or freshness.get('status')!='current' or type(freshness.get('generation'))is not int
        or any(r['index_generation']!=freshness.get('generation')for r in data._members)):return baseline
    candidate=apply_command_table_transaction(baseline,anchors)
    if candidate is baseline:return baseline
    from .context_budget import synchronize_estimate, estimate_payload_tokens
    from .context_record_loop_transaction import restore_whitelist
    candidate['query_handoff']['callable_evidence'].update(data._scope,
        boundary='certified_static_ui_tables_only_not_exhaustive_or_unique')
    synchronize_estimate(candidate)
    if estimate_payload_tokens(candidate)>min(1500,baseline['output_budget']['target_tokens'])or restore_whitelist(candidate,baseline)!=baseline:return baseline
    return candidate


def enrich_command_table(data,query,path,freshness):
    baseline=deepcopy(dict(data));baseline['source_freshness']=freshness
    baseline.setdefault('query_handoff',{})['path_context']=path
    if (command_table_receipt(data,pending=True)is None or query!=data.get('query') or snapshot(freshness)!=snapshot(data.get('source_freshness'))
        or protected_command_table(baseline,query,data._pool)):return baseline
    result=CommandTableContext(baseline);result._anchors=deepcopy(data._anchors);result._members=deepcopy(data._members);result._pool=deepcopy(data._pool)
    result._root=data._root;result._files=data._files;result._scope=deepcopy(data._scope)
    result._binding=(query,snapshot(dict(result)),snapshot(result._anchors),snapshot(result._members),snapshot(result._pool),str(result._root),result._files,snapshot(result._scope))
    return result


def accounting_command_table(data):
    from .context_compact import _compact_context
    baseline=_compact_context(dict(data));candidate=compact_command_table(data,baseline)
    if candidate is baseline:return data
    view=deepcopy(dict(data));view['wiki_matches']=deepcopy(data._members)
    view['query_handoff']['code_anchors']=deepcopy(data._anchors)
    return view
