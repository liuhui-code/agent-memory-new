"""Finite subject-bound explicit-axis List view; no SDK or runtime-effect claim."""
from copy import deepcopy
import hashlib
from pathlib import Path
import sqlite3
import weakref
from .query_output_loop_selection import snapshot
from .query_ui_vertical_guard import protected_vertical
from .query_ui_vertical_request import vertical_request, qualifier_matches
from .query_ui_vertical_scope import vertical_frames

_issued = {}
_ERRORS = (AttributeError, KeyError, TypeError, ValueError, OverflowError, OSError, UnicodeError, sqlite3.Error)


class VerticalContext(dict):
    def __copy__(self): return dict(self)
    def __deepcopy__(self, memo): return deepcopy(dict(self), memo)


def qualified_vertical(project, query, pool):
    from .ui_vertical_list_source import parse_vertical_list_file, API
    from .ui_vertical_inventory import inventory_vertical_file
    subject = vertical_request(query)
    if subject is None:
        return None
    frames = vertical_frames(project, pool, subject)
    if not frames or len(frames) > 3:
        return None
    root = Path(project.root).resolve()
    sources, proofs, files = {}, {}, []
    aggregate_bytes = 0
    scope_files = frames[0]['scope_files']
    if (type(scope_files) is not list
            or {f['file_path'] for f in scope_files} != set(frames[0]['pool_paths'])
            or len({f['file_path'] for f in scope_files}) != len(scope_files)):
        return None
    for metadata in scope_files:
        path = metadata['file_path']
        file = (root / path).resolve()
        if not file.is_relative_to(root) or file.suffix not in {'.ets', '.ts'}:
            return None
        with file.open('rb') as stream:
            raw = stream.read(2 * 1024 * 1024 + 1)
        aggregate_bytes += len(raw)
        if len(raw) > 2 * 1024 * 1024 or aggregate_bytes > 8 * 1024 * 1024:
            return None
        source = raw.decode('utf-8'); digest = hashlib.sha256(raw).hexdigest()
        group = [f for f in frames if f['path'] == path]
        names = {f['owner']['symbol'] for f in group}
        if metadata['source_digest'] != digest or any(f['file']['source_digest'] != digest for f in group):
            return None
        inventory = inventory_vertical_file(source, allow_templates=True, allow_literal_constants=True)
        if (inventory is None
                or {entry.name for entry in inventory.declarations
                    if qualifier_matches(subject, entry.name)} != names
                or any(qualifier_matches(subject, entry.local) or entry.local in API
                       for entry in inventory.imports)):
            return None
        # Inventory alone never proves a positive layout. A matching file still
        # passes the old strict parser on these exact complete source bytes.
        proof = parse_vertical_list_file(source, names) if names else {}
        if names and (proof is None or set(proof) != names or not hasattr(proof, 'declared_names')
                or {n for n in proof.declared_names if qualifier_matches(subject, n)} != names):
            return None
        sources[path] = source; proofs[path] = proof; files.append((path, digest))
    anchors, members = [], []
    for frame in frames:
        path, owner, build = frame['path'], frame['owner'], frame['build']
        proof = proofs[path][owner['symbol']]
        if (build is None or proof.get('positive') is not True
                or proof.get('kind') not in {'component', 'struct'}
                or (proof['owner_start'], proof['owner_end']) != (owner['start_line'], owner['end_line'])
                or (proof['build_start'], proof['build_end']) != (build['start_line'], build['end_line'])):
            return None
        lo, hi = build['start_line'], build['end_line']
        span = dict(symbol=build['symbol'], start_line=lo, end_line=hi)
        anchors.append(dict(file_path=path, symbol=build['symbol'], symbol_type=build['symbol_type'],
                            record_ids=[build['id']], record_type='code_symbol', source_ranges=[span],
                            read_window=dict(start_line=lo, end_line=hi), role='supporting',
                            source_excerpts=[dict(span, content='\n'.join(sources[path].splitlines()[lo-1:hi]),
                                                  truncated=False, source='validated_request_snapshot')]))
        members.append(build)
    return anchors, members, tuple(files), snapshot(frames)


def binding(data):
    return (snapshot(dict(data)), snapshot(data._anchors), snapshot(data._members),
            snapshot(data._pool), str(data._root), data._project.project_id,
            str(data._project.db_path), data._files, data._frames)


def issue(data):
    data._binding = binding(data)
    ident = id(data)
    seal = snapshot(data._binding)
    def retire(reference):
        entry = _issued.get(ident)
        if entry is not None and entry[0] is reference:
            _issued.pop(ident, None)
    _issued[ident] = (weakref.ref(data, retire), seal)
    return data


def bind_vertical_context(project, query, baseline, pool):
    try:
        if (vertical_request(query) is None or baseline.get('query') != query
                or baseline.get('project_id') != project.project_id
                or not isinstance(baseline.get('project_path'), str)
                or Path(baseline['project_path']).resolve() != Path(project.root).resolve()
                or protected_vertical(baseline, query, pool, pending=True)):
            return baseline
        result = qualified_vertical(project, query, pool)
        if result is None:
            return baseline
        anchors, members, files, frames = result
        data = VerticalContext(deepcopy(dict(baseline)))
        data._anchors = anchors; data._members = members; data._files = files; data._frames = frames
        data._pool = deepcopy(pool); data._root = Path(project.root).resolve(); data._project = project
        return issue(data)
    except _ERRORS:
        return baseline


def vertical_receipt(data, *, pending=False):
    entry = _issued.get(id(data))
    if type(data) is not VerticalContext or entry is None or entry[0]() is not data:
        return None
    try:
        if (snapshot(data._binding) != entry[1] or snapshot(binding(data)) != entry[1]
                or vertical_request(data.get('query')) is None
                or protected_vertical(data, data['query'], data._pool, pending=pending)
                or Path(data._project.root).resolve() != data._root):
            return None
        result = qualified_vertical(data._project, data['query'], data._pool)
        if result is None:
            return None
        anchors, members, files, frames = result
        if (snapshot(anchors), snapshot(members), files, frames) != (
                snapshot(data._anchors), snapshot(data._members), data._files, data._frames):
            return None
        return data._anchors
    except _ERRORS:
        return None


def compact_vertical(data, baseline):
    from .context_compact import _compact_context
    if baseline != _compact_context(dict(data)):
        return baseline
    from .context_record_loop_transaction import apply_record_loop_transaction, restore_whitelist
    from .context_budget import synchronize_estimate, estimate_payload_tokens
    anchors = vertical_receipt(data)
    freshness = data.get('source_freshness', {})
    if (anchors is None or freshness.get('status') != 'current'
            or type(freshness.get('generation')) is not int
            or any(r['index_generation'] != freshness['generation'] for r in data._members)):
        return baseline
    candidate = apply_record_loop_transaction(baseline, anchors)
    if candidate is baseline:
        return baseline
    candidate['query_handoff']['callable_evidence']['boundary'] = 'non_exhaustive_static_vertical_list_configuration_not_sdk_identity_or_effect'
    synchronize_estimate(candidate)
    if (estimate_payload_tokens(candidate) > min(1500, baseline['output_budget']['target_tokens'])
            or restore_whitelist(candidate, baseline) != baseline):
        return baseline
    return candidate


def enrich_vertical(data, query, path, freshness):
    baseline = deepcopy(dict(data)); baseline['source_freshness'] = freshness
    baseline.setdefault('query_handoff', {})['path_context'] = path
    if (vertical_receipt(data, pending=True) is None or query != data.get('query')
            or snapshot(freshness) != snapshot(data.get('source_freshness'))
            or protected_vertical(baseline, query, data._pool)):
        return baseline
    result = VerticalContext(baseline)
    for field in ('_anchors', '_members', '_pool'):
        setattr(result, field, deepcopy(getattr(data, field)))
    for field in ('_root', '_files', '_frames', '_project'):
        setattr(result, field, getattr(data, field))
    return issue(result)


def accounting_vertical(data):
    # This terminal presentation view does not change ordinary usage accounting.
    return dict(data)
