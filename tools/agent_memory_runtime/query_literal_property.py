# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Optional lexical navigation of already selected rows; never an identity alias."""
import hashlib
import sqlite3
from contextlib import closing
import re

from .literal_property_source import read_literal_source
from .storage import connect

ID = r'[A-Za-z_$][A-Za-z0-9_$]{0,63}'
PATH = rf'{ID}(?:\.{ID}){{2,7}}'
REQUEST = re.compile(rf'[ \t\r\n]*(?i:Locate)[ \t]+(?P<quote>`?)(?P<path>{PATH})(?P=quote)\.?[ \t\r\n]*')
IDENTITY = ('id', 'project_id', 'file_path', 'symbol', 'symbol_key', 'source_digest',
            'index_generation', 'start_line', 'end_line', 'literal_property_path')
BLOCK = ('typed_contract_match', 'typed_contract_weak', 'source_operation_match',
         'artifact_role_competition', 'artifact_role_representative', 'artifact_role_shadow',
         'excluded_by_query')


def positive(value):
    return type(value) is int and value > 0


def complete_pool(rows, files):
    paths = {f.get('file_path') for f in files}
    if not paths or {r.get('file_path') for r in rows} != paths:
        return False
    ids = [r.get('id') for r in rows]
    if not all(positive(i) for i in ids) or len(set(ids)) != len(ids):
        return False
    for path in paths:
        part = [r for r in rows if r['file_path'] == path]
        if any(type(r.get('source_count')) is not int or r['source_count'] != len(part) for r in part):
            return False
    return True



def fresh(project, row):
    if row.get('project_id') != project.project_id or not row.get('symbol_key'):
        return False
    try:
      with closing(connect(project)) as conn:
        states = conn.execute('SELECT generation,status FROM code_index_state WHERE project_id=?',
                              (project.project_id,)).fetchmany(2)
        files = conn.execute('SELECT source_digest,index_generation FROM code_files WHERE project_id=? AND file_path=?',
                             (project.project_id, row['file_path'])).fetchmany(2)
    except (sqlite3.Error, OSError):
        return False
    if len(states) != 1 or len(files) != 1:
        return False
    state, file = states[0], files[0]
    generation = row.get('index_generation')
    digest = row.get('source_digest')
    raw = read_literal_source(project, row['file_path'])
    return (state['status'] == 'active' and positive(state['generation']) and positive(generation)
            and generation == file['index_generation'] and generation <= state['generation']
            and isinstance(digest, str) and len(digest) == 64 and digest == file['source_digest']
            and raw is not None and hashlib.sha256(raw).hexdigest() == digest)


def prefer_literal_property(project, query, rows, files, ranked, selected):
    from .query_hierarchical_localization import protected_priority, compact_callable, valid_source_ranges
    from .query_callable_evidence import compact_candidate, certainty, certainty_alternatives
    match = REQUEST.fullmatch(query) if isinstance(query, str) else None
    if not match or not selected or not complete_pool(rows, files):
        return selected
    path = match['path']
    matches = [r for r in ranked if r.get('literal_property_path') == path]
    if len(matches) != 1:
        return selected
    target = matches[0]
    originals = [r for r in rows if all(r.get(k) == target.get(k) for k in IDENTITY)]
    if (len(originals) != 1 or not any(r is target for r in selected)
            or target.get('symbol') != path.rsplit('.', 1)[1]
            or not positive(target.get('start_line')) or not positive(target.get('end_line'))
            or target['end_line'] < target['start_line']
            or any(any(r.get(k) for k in BLOCK) for r in ranked)):
        return selected
    if any(type(r.get(k, False)) is not bool for r in ranked
           for k in ('explicit_owner_identity_match', 'target_owner_kind_match')
           if r.get(k) is not None):
        return selected
    index = next(i for i, r in enumerate(selected) if r is target)
    if index == 0 or any(protected_priority(r) != protected_priority(target) for r in selected[:index]):
        return selected
    proposed = [target, *selected[:index], *selected[index + 1:]]
    def confidence(items):
        compact = [compact_callable(r) for r in items]
        ranges = valid_source_ranges(items, query)
        prepared = [compact_candidate(r, ranges) for r in compact]
        return certainty(prepared[0], certainty_alternatives(compact, prepared))
    if confidence(selected) != 'bounded' and confidence(proposed) == 'bounded':
        return selected
    return proposed if fresh(project, target) else selected
