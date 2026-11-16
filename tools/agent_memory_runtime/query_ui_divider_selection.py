# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Finite request-bound static UI property view; never SDK or effect authority."""
from copy import deepcopy
import hashlib
from pathlib import Path
import sqlite3
from .query_output_loop_selection import snapshot
from .query_record_loop_selection import protected_record_loop
from .query_ui_divider_request import divider_request, qualifier_matches
from .query_ui_divider_scope import divider_frames


class DividerContext(dict):
    def __copy__(self): return dict(self)
    def __deepcopy__(self, memo): return deepcopy(dict(self), memo)


def qualified_divider(project, query, pool):
    from .ui_divider_source import parse_ui_divider_file
    qualifier = divider_request(query)
    if qualifier is None:
        return None
    frames = divider_frames(project, pool, qualifier)
    if frames is None:
        return None
    root = Path(project.root).resolve()
    sources, certificates, files = {}, {}, []
    for path in sorted({f['path'] for f in frames}):
        file = (root/path).resolve()
        if not file.is_relative_to(root) or file.suffix != '.ets':
            return None
        with file.open('rb') as stream:
            raw = stream.read(2*1024*1024+1)
        if len(raw) > 2*1024*1024:
            return None
        source = raw.decode('utf-8'); digest = hashlib.sha256(raw).hexdigest()
        group = [f for f in frames if f['path'] == path]
        if any(f['file']['source_digest'] != digest for f in group):
            return None
        proof = parse_ui_divider_file(source, [f['owner']['symbol'] for f in group])
        names = {f['owner']['symbol'] for f in group}
        if (proof is None or set(proof) != names or not hasattr(proof, 'declared_names')
                or {n for n in proof.declared_names if qualifier_matches(qualifier, n)} != names):
            return None
        sources[path] = source; certificates[path] = proof; files.append((path, digest))
    anchors, members = [], []
    for frame in frames:
        path, owner, build = frame['path'], frame['owner'], frame['build']
        proof = certificates[path][owner['symbol']]
        if ((proof['owner_start'], proof['owner_end']) != (owner['start_line'], owner['end_line'])
                or (proof['build_start'], proof['build_end']) != (build['start_line'], build['end_line'])):
            return None
        if not proof['positive']:
            continue
        lo, hi = build['start_line'], build['end_line']
        span = dict(symbol=build['symbol'], start_line=lo, end_line=hi)
        anchor = dict(file_path=path, symbol=build['symbol'], symbol_type=build['symbol_type'],
                      record_ids=[build['id']], record_type='code_symbol', source_ranges=[span],
                      read_window=dict(start_line=lo, end_line=hi), role='supporting',
                      source_excerpts=[dict(span, content='\n'.join(sources[path].splitlines()[lo-1:hi]),
                                            truncated=False, source='validated_request_snapshot')])
        anchors.append(anchor); members.append(build)
    return (anchors, members, tuple(files), snapshot(frames)) if anchors else None


def binding(data):
    return (data.get('query'), snapshot(dict(data)), snapshot(data._anchors), snapshot(data._members),
            snapshot(data._pool), str(data._root), data._files, data._frames)


def bind_divider_context(project, query, baseline, pool):
    if divider_request(query) is None or type(pool) is not list or any(type(r) is not dict for r in pool):
        return baseline
    if protected_record_loop(baseline, query, pool, pending=True):
        return baseline
    try:
        result = qualified_divider(project, query, pool)
    except (KeyError, TypeError, ValueError, OverflowError, OSError, UnicodeError, sqlite3.Error):
        return baseline
    if result is None:
        return baseline
    anchors, members, files, frames = result
    data = DividerContext(baseline)
    data._anchors = anchors; data._members = members; data._files = files; data._frames = frames
    data._pool = deepcopy(pool); data._root = Path(project.root).resolve(); data._project = project
    data._binding = binding(data)
    return data


def divider_receipt(data, *, pending=False):
    if not isinstance(data, DividerContext):
        return None
    try:
        if (data._binding != binding(data) or divider_request(data.get('query')) is None
                or protected_record_loop(data, data['query'], data._pool, pending=pending)
                or Path(data._project.root).resolve() != data._root):
            return None
        # Revalidate current DB identity/generation AND every examined source file,
        # including finite nonmatching frames. No source/metadata drift is accepted.
        result = qualified_divider(data._project, data['query'], data._pool)
        if result is None:
            return None
        anchors, members, files, frames = result
        if (snapshot(anchors), snapshot(members), files, frames) != (
                snapshot(data._anchors), snapshot(data._members), data._files, data._frames):
            return None
        return data._anchors
    except (AttributeError, KeyError, TypeError, ValueError, OverflowError, OSError, UnicodeError, sqlite3.Error):
        return None


def compact_divider(data, baseline):
    from .context_record_loop_transaction import apply_record_loop_transaction, restore_whitelist
    from .context_budget import synchronize_estimate, estimate_payload_tokens
    anchors = divider_receipt(data)
    freshness = data.get('source_freshness', {})
    if (anchors is None or freshness.get('status') != 'current'
            or type(freshness.get('generation')) is not int
            or any(r['index_generation'] != freshness['generation'] for r in data._members)):
        return baseline
    candidate = apply_record_loop_transaction(baseline, anchors)
    if candidate is baseline:
        return baseline
    candidate['query_handoff']['callable_evidence']['boundary'] = 'non_exhaustive_static_ui_configuration_not_sdk_identity_or_effect'
    synchronize_estimate(candidate)
    if (estimate_payload_tokens(candidate) > min(1500, baseline['output_budget']['target_tokens'])
            or restore_whitelist(candidate, baseline) != baseline):
        return baseline
    return candidate


def enrich_divider(data, query, path, freshness):
    baseline = deepcopy(dict(data)); baseline['source_freshness'] = freshness
    baseline.setdefault('query_handoff', {})['path_context'] = path
    if (divider_receipt(data, pending=True) is None or query != data.get('query')
            or snapshot(freshness) != snapshot(data.get('source_freshness'))
            or protected_record_loop(baseline, query, data._pool)):
        return baseline
    result = DividerContext(baseline)
    for field in ('_anchors', '_members', '_pool'):
        setattr(result, field, deepcopy(getattr(data, field)))
    for field in ('_root', '_files', '_frames', '_project'):
        setattr(result, field, getattr(data, field))
    result._binding = binding(result)
    return result


def accounting_divider(data):
    from .context_compact import _compact_context
    baseline = _compact_context(dict(data)); candidate = compact_divider(data, baseline)
    if candidate is baseline:
        return data
    view = deepcopy(dict(data)); view['wiki_matches'] = deepcopy(data._members)
    view['query_handoff']['code_anchors'] = deepcopy(data._anchors)
    return view
