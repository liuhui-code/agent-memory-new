# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Request-bound positive scan syntax; unknown candidates are not absent."""
from copy import deepcopy
import hashlib
from pathlib import Path
from .storage import connect
from .query_output_loop_selection import valid_row, protected, snapshot
from .query_cache_scan_source import cache_scan_request, parse_cache_scan_source


class CacheScanContext(dict):
    def __copy__(self):
        return dict(self)
    def __deepcopy__(self, memo):
        return deepcopy(dict(self), memo)


def bind_cache_scan_context(project, query, baseline):
    if not cache_scan_request(query) or protected(baseline):
        return baseline
    pool = baseline.get('wiki_matches') or []
    paths = sorted({r.get('file_path') for r in pool if isinstance(r.get('file_path'), str)})
    if not paths or len(paths) > 12:
        return baseline
    with connect(project) as conn:
        marks = ','.join('?' for _ in paths)
        args = [project.project_id, *paths]
        rows = [dict(r) for r in conn.execute('SELECT * FROM code_symbols WHERE project_id=? AND file_path IN ('+marks+')', args)]
        files = [dict(r) for r in conn.execute('SELECT * FROM code_files WHERE project_id=? AND file_path IN ('+marks+')', args)]
    selected = []; receipts = []; members = []; root = Path(project.root).resolve()
    for name in paths:
        try:
            file = (root/name).resolve()
            if not file.is_relative_to(root):
                return baseline
            if file.suffix not in {'.ts', '.ets'}:
                continue
            with file.open('rb') as stream:
                raw = stream.read(2*1024*1024+1)
            if len(raw) > 2*1024*1024:
                continue
            source = raw.decode('utf-8')
            parsed = parse_cache_scan_source(source)
        except (OSError, UnicodeError):
            continue
        if parsed is None:
            continue
        digest = hashlib.sha256(raw).hexdigest()
        local = [r for r in rows if r['file_path'] == name]
        owners = [r for r in local if r['symbol_type'] == 'class' and r['symbol'] == parsed['owner']]
        file_rows = [r for r in files if r['file_path'] == name]
        if len(owners) != 1 or len(file_rows) != 1:
            return baseline
        owner = owners[0]; f = file_rows[0]
        if (not valid_row(owner, project) or owner.get('qualified_name') != parsed['owner']
                or owner.get('owner_name') not in {'', None} or not owner.get('owner_kind')
                or owner['source_digest'] != digest
                or f.get('source_digest') != digest or f.get('index_generation') != owner['index_generation']
                or (owner['start_line'], owner['end_line']) != (parsed['class_start'], parsed['class_end'])):
            return baseline
        matching = [r for r in local if r['symbol'] == parsed['method']
                    and r['qualified_name'] == parsed['owner']+'.'+parsed['method']
                    and r['owner_name'] == parsed['owner'] and r['owner_kind'] == owner['owner_kind']
                    and r['symbol_type'] in {'method', 'function'}
                    and (r['start_line'], r['end_line']) == (parsed['start_line'], parsed['end_line'])]
        if len(matching) != 1:
            return baseline
        row = matching[0]
        if (not valid_row(row, project) or row['source_digest'] != digest
                or row['index_generation'] != owner['index_generation']):
            return baseline
        fields = ('id', 'project_id', 'file_path', 'symbol', 'symbol_key', 'qualified_name',
                  'start_line', 'end_line', 'source_digest', 'index_generation',
                  'owner_name', 'owner_kind', 'semantic_adapter', 'evidence_class', 'symbol_type')
        for bound in (owner, row):
            aliases = [r for r in rows if r.get('id') == bound['id'] or r.get('symbol_key') == bound['symbol_key']]
            if any(any(r.get(k) != bound.get(k) for k in fields) for r in aliases):
                return baseline
        recalled = [r for r in pool if r.get('file_path') == name and
                    (r.get('id') == row['id'] or r.get('symbol_key') == row['symbol_key'])]
        if not recalled or any(r.get('kind') != 'symbol' or any(r.get(k) != row[k] for k in fields) for r in recalled):
            return baseline
        members.extend(recalled[:1])
        selected.append(dict(source='wiki',record_id=row['id'],record_type='code_symbol',file_path=name,
            symbol=row['symbol'],symbol_type=row['symbol_type'],start_line=row['start_line'],end_line=row['end_line']))
        receipts.append((name,digest,tuple(source.splitlines()),((row['symbol'],row['start_line'],row['end_line']),)))
    if not receipts or len(receipts) > 3:
        return baseline
    view = deepcopy(dict(baseline)); view['wiki_matches'] = deepcopy(members)
    view['query_handoff']['code_anchors'] = selected
    view['query_handoff']['callable_evidence'] = {
        'schema_version':'agent-callable-evidence/v1', 'certainty':'uncertain',
        'primary':None, 'alternatives':[],
        'boundary':'positive_static_minimum_field_scan_delete_syntax_non_exhaustive_runtime_eviction_and_timestamp_unproven'}
    from .context_compact import _compact_context
    receipts = tuple(receipts)
    if not complete_snapshot_projection(_compact_context(view,cache_scan_receipts=receipts),receipts):
        return baseline
    result = CacheScanContext(baseline); result._view = view; result._receipts = receipts
    result._binding = (query,snapshot(dict(result)),snapshot(view),receipts)
    return result


def cache_scan_context_view(data):
    if not isinstance(data, CacheScanContext):
        return data, None
    try:
        current = (data.get('query'),snapshot(dict(data)),snapshot(data._view),data._receipts)
        if current != data._binding or not cache_scan_request(data.get('query')):
            return dict(data), None
        return data._view, data._receipts
    except (AttributeError, TypeError, ValueError):
        return dict(data), None


def attach_cache_scan_excerpts(payload,receipts,token_budget):
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
                    source='validated_request_snapshot',selection_reason='static_minimum_field_scan_delete',truncated=actual_end<end))
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


def enrich_cache_scan_context(data,query,path_payload,freshness):
    """Only the trusted Facade's empty-path enrichment can transport a receipt."""
    baseline=deepcopy(dict(data))
    baseline['source_freshness']=freshness
    baseline.setdefault('query_handoff',{})['path_context']=path_payload
    view,receipts=cache_scan_context_view(data)
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
    if not complete_snapshot_projection(_compact_context(view,cache_scan_receipts=receipts),receipts):
        return baseline
    result=CacheScanContext(baseline);result._view=view;result._receipts=receipts
    result._binding=(query,snapshot(dict(result)),snapshot(view),receipts)
    return result
