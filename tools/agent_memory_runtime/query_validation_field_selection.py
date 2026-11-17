# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Atomic finite guarded-field view, never unique owner or runtime causality."""
from copy import deepcopy
from pathlib import Path
import sqlite3
import weakref
from .query_output_loop_selection import snapshot
from .query_record_loop_selection import protected_record_loop
from .query_validation_field_scope import validation_field_scope
from .query_validation_no_logs import validation_no_logs, check_validation_no_logs

# External issuance seal is immutable; receipt attributes are not authority.
_issued = {}
_ERRORS = (AttributeError, KeyError, TypeError, ValueError, OverflowError, OSError, UnicodeError, sqlite3.Error, StopIteration)


class ValidationContext(dict):
    def __copy__(self): return dict(self)
    def __deepcopy__(self, memo): return deepcopy(dict(self), memo)


def protected(data, query, pool, *, pending=False):
    try:
        count = data['query_audit']['candidate_recall']['tables']['code_log_statements']['candidate_count']
        logs = data['query_handoff']['log_anchors']
        return (type(count) is not int or count != 0 or type(logs) is not list or bool(logs)
                or protected_record_loop(data, query, pool, pending=pending))
    except _ERRORS:
        return True


def binding(data):
    return (snapshot(dict(data)), snapshot(data._anchors), snapshot(data._members),
            snapshot(data._pool), str(data._root), data._project.project_id, data._files, data._state, id(data._collection), id(data._no_logs),
            snapshot(data._collection.matches), snapshot(data._collection.recall_audit))


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


def bind_validation_field_context(project, query, data, items, collection=None):
    from .query_validation_field_request import validation_field_request
    try:
        permission = validation_field_request(query)
        no_logs = validation_no_logs(project, query, collection)
        if no_logs is None:
            return data
        if (permission is None or data.get('query') != query
                or data.get('project_id') != project.project_id
                or not isinstance(data.get('project_path'), str)
                or Path(data['project_path']).resolve() != Path(project.root).resolve()
                or protected(data, query, items, pending=True)):
            return data
        result = validation_field_scope(project, permission, items)
        if result is None:
            return data
        anchors, members, files, state = result
        bound = ValidationContext(deepcopy(dict(data)))
        bound._collection = collection; bound._no_logs = no_logs
        bound._anchors = anchors; bound._members = members; bound._files = files; bound._state = state
        bound._pool = deepcopy(items); bound._project = project; bound._root = Path(project.root).resolve()
        return issue(bound)
    except _ERRORS:
        return data


def validation_field_receipt(data, *, pending=False):
    from .query_validation_field_request import validation_field_request
    entry = _issued.get(id(data))
    if type(data) is not ValidationContext or entry is None or entry[0]() is not data:
        return None
    try:
        if not check_validation_no_logs(data._project, data.get('query'), data._collection, data._no_logs):
            return None
        permission = validation_field_request(data.get('query'))
        if (permission is None or snapshot(data._binding) != entry[1]
                or snapshot(binding(data)) != entry[1] or data._binding != binding(data)
                or Path(data._project.root).resolve() != data._root
                or protected(data, data['query'], data._pool, pending=pending)):
            return None
        result = validation_field_scope(data._project, permission, data._pool)
        if result is None:
            return None
        anchors, members, files, state = result
        if (snapshot(anchors), snapshot(members), files, state) != (
                snapshot(data._anchors), snapshot(data._members), data._files, data._state):
            return None
        return data._anchors
    except _ERRORS:
        return None


def compact_validation_field(data, baseline):
    from .context_record_loop_transaction import apply_record_loop_transaction, restore_whitelist
    from .context_budget import synchronize_estimate, estimate_payload_tokens
    from .context_compact import _compact_context
    try:
        if validation_field_receipt(data) is None or baseline != _compact_context(dict(data)):
            return baseline
        fresh = data.get('source_freshness', {})
        if (fresh.get('status') != 'current' or type(fresh.get('generation')) is not int
                or any(r['index_generation'] != fresh['generation'] for r in data._members)):
            return baseline
        candidate = apply_record_loop_transaction(baseline, data._anchors)
        if candidate is baseline:
            return baseline
        candidate['query_handoff']['callable_evidence']['boundary'] = 'non_exhaustive_static_guarded_field_dispatch_not_unique_owner_or_runtime_causality'
        synchronize_estimate(candidate)
        if (estimate_payload_tokens(candidate) > min(1500, baseline['output_budget']['target_tokens'])
                or restore_whitelist(candidate, baseline) != baseline):
            return baseline
        return candidate
    except _ERRORS:
        return baseline


def enrich_validation_field(data, query, path, freshness):
    baseline = deepcopy(dict(data)); baseline['source_freshness'] = freshness
    baseline.setdefault('query_handoff', {})['path_context'] = path
    try:
        if (validation_field_receipt(data, pending=True) is None or query != data.get('query')
                or snapshot(freshness) != snapshot(data.get('source_freshness'))
                or protected(baseline, query, data._pool)):
            return baseline
        result = ValidationContext(baseline)
        for field in ('_anchors', '_members', '_pool'):
            setattr(result, field, deepcopy(getattr(data, field)))
        for field in ('_root', '_files', '_state', '_project', '_collection', '_no_logs'):
            setattr(result, field, getattr(data, field))
        return issue(result)
    except _ERRORS:
        return baseline


def accounting_validation_field(data):
    from .context_compact import _compact_context
    baseline = _compact_context(dict(data))
    if compact_validation_field(data, baseline) is baseline:
        return data
    view = deepcopy(dict(data)); view['wiki_matches'] = deepcopy(data._members)
    view['query_handoff']['code_anchors'] = deepcopy(data._anchors)
    return view
