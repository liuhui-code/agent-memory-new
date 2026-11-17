"""Private bounded trial callback set; static syntax, never runtime touch safety."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3

from .storage import connect
from .query_command_table_scope import IDENTITY, FILE_FIELDS, same_fields, symbol_alias
from .query_output_loop_selection import valid_row, snapshot
from .query_record_loop_selection import protected_record_loop
from .ui_touch_index_source import parse_touch_index_file


_ISSUER = object()


class TouchIndexContext(dict):
    def __copy__(self): return dict(self)
    def __deepcopy__(self, memo): return deepcopy(dict(self), memo)


def protected_touch(data, query, pool, *, pending=False, log_witness=None):
    try:
        h = data['query_handoff']
        count = data['query_audit']['candidate_recall']['tables']['code_log_statements']['candidate_count']
        if type(count) is not int or count < 0 or (count != 0 and log_witness is None):
            return True
        return (type(h) is not dict or type(h.get('log_anchors')) is not list
                or (bool(h['log_anchors']) and log_witness is None)
                or protected_record_loop(data, query, pool, pending=pending))
    except (AttributeError, KeyError, TypeError, ValueError):
        return True


def log_witness(project, data, inventory, query, pool, *, pending=False):
    """Independent complete candidate evidence, not permission to remove query guards."""
    try:
        if inventory is None:return None
        from .query_touch_log_provenance import touch_log_provenance
        from .query_touch_index_trial import log_candidate_rows
        inventory=log_candidate_rows(project,query,inventory)
        count=data['query_audit']['candidate_recall']['tables']['code_log_statements']['candidate_count']
        if (type(inventory)is not dict or set(inventory)!={'direct','effects'}
                or any(type(inventory[k])is not list for k in inventory)
                or type(count)is not int or count!=len(inventory['direct'])):return None
        # All candidates retain original-query event/owner/identity protection,
        # including rows that ordinary scoring did not display. No public edit.
        guards=deepcopy(dict(data));guards['query_handoff']['log_anchors']=deepcopy(
            data['query_handoff']['log_anchors']+inventory['direct']+inventory['effects'])
        if protected_record_loop(guards,query,pool,pending=pending):return None
        return touch_log_provenance(project,inventory,data['query_handoff']['log_anchors'])
    except(AttributeError,KeyError,TypeError,ValueError,sqlite3.Error):return None


def fresh_pair(baseline, trial):
    """Empty ordinary recall is not current source authority; trial proves sources."""
    try:
        before=baseline['source_freshness']; after=trial['source_freshness']
        generation=after['generation']
        if (type(before)is not dict or type(after)is not dict
                or type(generation)is not int or generation<=0
                or type(before.get('generation'))is not int or before['generation']!=generation
                or after.get('status')!='current' or before.get('status')not in {'empty','current'}):return False
        for value in (before,after):
            if (type(value.get('blocked_rows'))is not int or value['blocked_rows']!=0
                    or type(value.get('blocked_rows_by_table'))is not dict
                    or any(type(n)is not int or n!=0 for n in value['blocked_rows_by_table'].values())
                    or any(type(value.get(k))is not list or value[k] for k in
                           ('stale_paths','missing_paths','unverified_paths','boundary_drift_scope_ids'))):return False
            counts=[value.get(k)for k in ('candidate_file_count','checked_file_count','current_file_count')]
            if any(type(n)is not int or n<0 for n in counts)or len(set(counts))!=1:return False
            if value['status']=='empty'and any(counts):return False
            if value['status']=='current'and not all(counts):return False
        state=json.loads(trial._state)
        current=state['states']['code_index_state']
        return len(current)==1 and type(current[0]['generation'])is int and current[0]['generation']==generation
    except(AttributeError,KeyError,TypeError,ValueError):return False


def qualified_touch_index(project, pool):
    """Validate admitted paths and original callback identities, never DB recall."""
    if type(pool) is not list or not pool or any(type(r) is not dict for r in pool):
        return None
    paths = set()
    for row in pool:
        path = row.get('file_path')
        if (row.get('kind') not in {'file', 'symbol'} or not isinstance(path, str)
                or not path or Path(path).is_absolute() or '..' in Path(path).parts):
            return None
        paths.add(path)
    if len(paths) > 12: return None
    root = Path(project.root).resolve()
    with connect(project) as db:
        marks = ','.join('?' for _ in paths); args = (project.project_id, *sorted(paths))
        files = [dict(r) for r in db.execute('SELECT * FROM code_files WHERE project_id=? AND file_path IN ('+marks+')', args)]
        rows = [dict(r) for r in db.execute('SELECT * FROM code_symbols WHERE project_id=? AND file_path IN ('+marks+')', args)]
        verified = {}; recalled_files = {}
        for item in pool:
            if item['kind'] == 'file':
                matches = [r for r in files if r['id'] == item.get('id') or r['file_path'] == item['file_path']]
                if len(matches) != 1 or not same_fields(item, matches[0], FILE_FIELDS):
                    return None
                recalled_files[item['file_path']] = matches[0]
            else:
                ident, key = item.get('id'), item.get('symbol_key')
                if type(ident) is not int or ident <= 0 or (key is not None and not isinstance(key, str)):
                    return None
                clause = 'id=?'; values = (project.project_id, ident)
                if isinstance(key, str) and key:
                    clause += ' OR symbol_key=?'; values += (key,)
                aliases = [dict(r) for r in db.execute('SELECT * FROM code_symbols WHERE project_id=? AND ('+clause+') LIMIT 2', values)]
                if len(aliases) != 1 or not same_fields(item, aliases[0], IDENTITY):
                    return None
                if ident in verified and not same_fields(verified[ident], item, IDENTITY):
                    return None
                verified[ident] = aliases[0]
    anchors = []; members = []; sources = []; frames = []
    for name in sorted(paths):
        file = (root/name).resolve()
        if not file.is_relative_to(root): return None
        with file.open('rb') as stream: raw = stream.read(2*1024*1024+1)
        if len(raw) > 2*1024*1024: return None
        digest = hashlib.sha256(raw).hexdigest()
        metadata = [r for r in files if r['file_path'] == name]
        if (len(metadata) != 1 or metadata[0]['source_digest'] != digest
                or type(metadata[0]['index_generation']) is not int):
            return None
        f = metadata[0]
        for row in verified.values():
            if row['file_path'] == name and (not valid_row(row, project)
                    or row['source_digest'] != digest or row['index_generation'] != f['index_generation']):
                return None
        sources.append((name, digest))
        frame=dict(path=name, file=f, admitted=[r for r in verified.values() if r['file_path']==name], owner_witnesses=[])
        frames.append(frame)
        if file.suffix != '.ets': continue
        source = raw.decode('utf-8')
        proof = parse_touch_index_file(source)
        # Unknown source is not an absence or global exclusion certificate.
        if proof is None: continue
        local = [r for r in rows if r['file_path'] == name]
        for owner_name, parsed in sorted(proof.items()):
            owners = [r for r in local if r['symbol'] == owner_name and not r.get('owner_name')
                      and r['symbol_type'] in {'component', 'struct'}]
            if len(owners) != 1: return None
            owner = owners[0]
            if (owner['owner_kind'] != 'component'
                    or owner['qualified_name'] != owner_name
                    or (owner['start_line'],owner['end_line']) != (parsed['owner_start'],parsed['owner_end'])):
                return None
            with connect(project) as db:
                aliases = [dict(r) for r in db.execute(
                    'SELECT * FROM code_symbols WHERE project_id=? AND (id=? OR symbol_key=?) LIMIT 2',
                    (project.project_id, owner['id'], owner['symbol_key']))]
            if len(aliases)!=1 or not same_fields(owner,aliases[0],IDENTITY): return None
            frame['owner_witnesses'].append(owner)
            builds = [r for r in verified.values() if r['file_path']==name and r.get('owner_name')==owner_name and r['symbol']=='build']
            if len(builds) != 1: return None
            build = builds[0]
            if (build['qualified_name'] != owner_name+'.build' or build['signature'] != 'build():unknown'
                    or build['owner_kind'] != 'component' or build['symbol_type'] not in {'function','method'}
                    or (build['start_line'],build['end_line']) != (parsed['build_start'],parsed['build_end'])):
                return None
            lo, hi = parsed['callback_start'], parsed['callback_end']
            callbacks = [r for r in verified.values() if r['file_path']==name and r.get('owner_name')==owner_name
                         and r['symbol']==parsed['callback_name'] and r['signature']=='callback onTouch@'+str(lo)
                         and r['qualified_name']==owner_name+'.onTouch@'+str(lo)]
            if len(callbacks) != 1: return None
            callback = callbacks[0]
            if (callback['symbol_type'] not in {'function','method'} or callback['owner_kind']!='component'
                    or (callback['start_line'],callback['end_line']) != (lo,hi)
                    or not owner['start_line'] <= build['start_line'] <= lo <= hi <= build['end_line'] <= owner['end_line']):
                return None
            for row in (owner, build, callback):
                aliases = [r for r in rows if symbol_alias(row,r)]
                if (len(aliases)!=1 or not same_fields(row,aliases[0],IDENTITY) or not valid_row(row,project)
                        or row['source_digest']!=digest or row['index_generation']!=f['index_generation']):
                    return None
            span = dict(symbol=callback['symbol'],start_line=lo,end_line=hi)
            anchors.append(dict(file_path=name,symbol=callback['symbol'],symbol_type=callback['symbol_type'],
                record_ids=[callback['id']],record_type='code_symbol',source_ranges=[span],
                read_window=dict(start_line=lo,end_line=hi),role='supporting',source_excerpts=[dict(span,
                    content='\n'.join(source.splitlines()[lo-1:hi]),truncated=False,source='validated_request_snapshot')]))
            members.append(callback)
    if not 0 < len(anchors) <= 3 or len({(r['file_path'],r['id']) for r in members}) != len(members):
        return None
    return anchors,members,tuple(sources),snapshot(frames)


def binding(data):
    return (data.get('query'),snapshot(dict(data)),snapshot(data._anchors),snapshot(data._members),
            snapshot(data._pool),data._files,data._frames,str(data._root),snapshot(dict(data._trial)),data._baseline_signature,data._log_witnesses)


def bind_touch_index_context(project, query, baseline, trial):
    from .query_touch_index_trial import valid_trial
    try:
        before=log_witness(project,baseline,getattr(trial,'_baseline_logs',None),query,trial._pool,pending=True)
        after=log_witness(project,trial,getattr(trial,'_trial_logs',None),query,trial._pool,pending=True)
        if before is None or after is None:return baseline
        if (baseline.get('query') != query or baseline.get('project_id') != project.project_id
                or Path(baseline['project_path']).resolve() != Path(project.root).resolve()
                or not valid_trial(project,query,trial)
                or snapshot(baseline)!=trial._baseline_signature
                or not fresh_pair(baseline,trial)
                or protected_touch(baseline,query,trial._pool,pending=True,log_witness=before)
                or protected_touch(trial,query,trial._pool,pending=True,log_witness=after)):
            return baseline
        result = qualified_touch_index(project,trial._pool)
        if result is None: return baseline
        anchors,members,files,frames = result
        data = TouchIndexContext(baseline); data._issuer=_ISSUER; data._anchors=anchors; data._members=members
        data._pool=deepcopy(trial._pool); data._files=files; data._frames=frames
        data._trial=trial; data._baseline_signature=trial._baseline_signature; data._project=project; data._root=Path(project.root).resolve()
        data._log_witnesses=(before,after)
        data._binding=binding(data)
        return data
    except (AttributeError,KeyError,TypeError,ValueError,OverflowError,OSError,UnicodeError,sqlite3.Error):
        return baseline


def touch_index_receipt(data, *, pending=False):
    from .query_touch_index_trial import valid_trial
    if type(data) is not TouchIndexContext or getattr(data,'_issuer',None) is not _ISSUER: return None
    try:
        before=log_witness(data._project,data,getattr(data._trial,'_baseline_logs',None),data['query'],data._pool,pending=pending)
        after=log_witness(data._project,data._trial,getattr(data._trial,'_trial_logs',None),data['query'],data._pool,pending=True)
        if before is None or after is None or (before,after)!=data._log_witnesses:return None
        if (data._binding != binding(data) or Path(data._project.root).resolve()!=data._root
                or not valid_trial(data._project,data['query'],data._trial)
                or data._baseline_signature!=data._trial._baseline_signature
                or not fresh_pair(data,data._trial)
                or protected_touch(data,data['query'],data._pool,pending=pending,log_witness=before)
                or protected_touch(data._trial,data['query'],data._pool,pending=True,log_witness=after)):
            return None
        result=qualified_touch_index(data._project,data._pool)
        if result is None: return None
        anchors,members,files,frames=result
        if (snapshot(anchors),snapshot(members),files,frames)!=(snapshot(data._anchors),snapshot(data._members),data._files,data._frames):
            return None
        return data._anchors
    except (AttributeError,KeyError,TypeError,ValueError,OverflowError,OSError,UnicodeError,sqlite3.Error):
        return None


def compact_touch_index(data, baseline):
    from .context_record_loop_transaction import apply_record_loop_transaction,restore_whitelist
    from .context_budget import synchronize_estimate,estimate_payload_tokens
    anchors=touch_index_receipt(data)
    if anchors is None:return baseline
    freshness=data._trial.get('source_freshness',{})
    if (freshness.get('status')!='current' or type(freshness.get('generation')) is not int
            or any(r['index_generation']!=freshness['generation'] for r in data._members)
            or any(f['file']['index_generation']!=freshness['generation'] for f in json.loads(data._frames))):
        return baseline
    result=apply_record_loop_transaction(baseline,anchors)
    if result is baseline:return baseline
    result['query_handoff']['callable_evidence']['boundary']='non_exhaustive_static_touch_index_callback_current_source_receipt_ordinary_freshness_unchanged_not_sdk_safety_or_cause'
    synchronize_estimate(result)
    if (estimate_payload_tokens(result)>min(1500,baseline['output_budget']['target_tokens'])
            or restore_whitelist(result,baseline)!=baseline):return baseline
    return result


def enrich_touch_index(data, query, path, freshness):
    baseline=deepcopy(dict(data));baseline['source_freshness']=freshness
    baseline.setdefault('query_handoff',{})['path_context']=path
    if (touch_index_receipt(data,pending=True) is None or query!=data.get('query')
            or snapshot(freshness)!=snapshot(data.get('source_freshness'))
            or protected_touch(baseline,query,data._pool,log_witness=data._log_witnesses[0])):return baseline
    result=TouchIndexContext(baseline); result._issuer=_ISSUER
    for field in ('_anchors','_members','_pool'):setattr(result,field,deepcopy(getattr(data,field)))
    for field in ('_files','_frames','_trial','_root','_project','_baseline_signature','_log_witnesses'):setattr(result,field,getattr(data,field))
    result._binding=binding(result)
    return result


def accounting_touch_index(data):
    # Facade has no presentation mode: only ordinary baseline usage is recorded.
    return dict(data)
