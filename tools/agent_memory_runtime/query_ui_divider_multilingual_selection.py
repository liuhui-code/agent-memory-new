"""Finite explicit-negative source view, rooted only in recalled build methods."""
from .query_output_loop_selection import snapshot
from .query_ui_divider_method_scope import method_rooted_frames
from .query_ui_divider_negative import resolve_negative_declarations, exclusion_intersection
from .query_ui_divider_request import qualifier_matches
from .ui_divider_source import parse_ui_divider_file


def qualified_multilingual_divider(project, descriptor, pool):
    if not descriptor.excluded_names:
        return None
    result = method_rooted_frames(project, pool, descriptor.qualifiers)
    if result is None:
        return None
    frames, sources, files, witnesses = result
    proofs = {}
    # All union frames verified before exclusions. Missing/unknown is not absence.
    for path in sorted({f['path'] for f in frames}):
        group = [f for f in frames if f['path'] == path]; names = {f['owner']['symbol'] for f in group}
        proof = parse_ui_divider_file(sources[path], names)
        if (proof is None or set(proof) != names
                or {n for n in proof.declared_names if any(qualifier_matches(t, n) for t in descriptor.qualifiers)} != names):
            return None
        for frame in group:
            row = proof[frame['owner']['symbol']]
            if (row['owner_start'], row['owner_end'], row['build_start'], row['build_end']) != (
                    frame['owner']['start_line'], frame['owner']['end_line'], frame['build']['start_line'], frame['build']['end_line']):
                return None
        proofs[path] = proof
    negative = resolve_negative_declarations(project, descriptor.excluded_names)
    if negative is None:
        return None
    resolved, negative_files = negative
    excluded = {(r['declaration']['file_path'], r['declaration']['id']) for r in resolved if r['declaration'] is not None}
    anchors, members = [], []
    for frame in frames:
        path, owner, build = frame['path'], frame['owner'], frame['build']
        if not proofs[path][owner['symbol']]['positive'] or (path, owner['id']) in excluded:
            continue
        lo, hi = build['start_line'], build['end_line']; span = dict(symbol=build['symbol'], start_line=lo, end_line=hi)
        anchors.append(dict(file_path=path, symbol=build['symbol'], symbol_type=build['symbol_type'],
                            record_ids=[build['id']], record_type='code_symbol', source_ranges=[span],
                            read_window=dict(start_line=lo, end_line=hi), role='supporting',
                            source_excerpts=[dict(span, content='\n'.join(sources[path].splitlines()[lo-1:hi]),
                                                  truncated=False, source='validated_request_snapshot')]))
        members.append(build)
    if not anchors or exclusion_intersection(anchors, resolved):
        return None
    receipt = dict(contract='multilingual-negative-static-divider/v1',
                   descriptor=dict(qualifiers=descriptor.qualifiers, excluded_names=descriptor.excluded_names,
                                   negative_spans=descriptor.negative_spans),
                   original_roots=[{k: r.get(k) for k in ('id', 'symbol_key', 'file_path', 'owner_name', 'source_digest', 'index_generation')}
                                   for r in pool if r.get('kind') == 'symbol' and r.get('symbol') == 'build'],
                   frames=frames, identity_witnesses=witnesses, negative_identities=resolved)
    return anchors, members, tuple(sorted(set(files+negative_files))), snapshot(receipt)
