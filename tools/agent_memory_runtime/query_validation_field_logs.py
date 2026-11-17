# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Same-pass nonempty validation lane; old absence route stays separate."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from .query_validation_binding_resources import bounded_binding_parts
from .query_validation_log_capture import bounded_metadata, validation_logs, validation_log_inventory
from .query_validation_log_provenance import verify_validation_logs
from .query_validation_field_log_guards import complete_candidate_rejections
from .query_validation_field_request import validation_field_request
from .query_validation_field_scope import validation_field_scope
from .query_output_loop_selection import snapshot


def preflight(data, pool, collection):
    from .query_validation_field_selection import ValidationContext
    if type(data) not in (dict, ValidationContext) or type(pool) is not list:
        return False
    # Shallow exact-dict view only; no recursive copy precedes finite traversal.
    return bounded_metadata([dict(data), pool, collection.matches, collection.recall_audit])


def check(project, query, data, pool, collection, capture, *, pending):
    if not preflight(data, pool, collection):
        return None
    permission = validation_field_request(query)
    if (permission is None or data.get('query') != query
            or data.get('project_id') != project.project_id
            or type(data.get('project_path')) is not str
            or Path(data['project_path']).resolve() != Path(project.root).resolve()
            or validation_logs(project, query, collection) is not capture or capture is None):
        return None
    inventory = validation_log_inventory(project, capture)
    if inventory is None or any(type(row) is not dict for row in pool):
        return None
    paths = [row.get('file_path') for row in pool]
    if any(type(path) is not str for path in paths) or sorted(set(paths)) != inventory['scope_paths']:
        return None
    count = data['query_audit']['candidate_recall']['tables']['code_log_statements']['candidate_count']
    if type(count) is not int or count < 0:
        return None
    if complete_candidate_rejections(project, query, collection, capture, dict(data), pool, pending=pending):
        return None
    result = validation_field_scope(project, permission, pool)
    if result is None:
        return None
    proof = verify_validation_logs(project, capture, data['query_handoff']['log_anchors'], inventory['scope_paths'])
    if proof is None:
        return None
    return (*result, proof)


def log_binding(data):
    if hasattr(data, '_no_logs'):
        raise ValueError('mixed validation lanes')
    metadata = [dict(data), data._anchors, data._members, data._pool,
                str(data._root), str(Path(data._project.root).resolve()),
                data._project.project_id, str(Path(data._project.db_path).resolve()),
                id(data._collection), id(data._log_capture),
                data._collection.matches, data._collection.recall_audit]
    if not bounded_binding_parts(metadata, data._files, data._state, data._log_proof):
        raise ValueError('binding resource limit')
    payload = [metadata, data._files, data._state, data._log_proof]
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    return ('validation-field-logs/v1', hashlib.sha256(encoded.encode('utf-8')).hexdigest())


def bind_logs(project, query, data, pool, collection):
    from .query_validation_field_selection import ValidationContext, issue
    capture = validation_logs(project, query, collection)
    result = check(project, query, data, pool, collection, capture, pending=True)
    if result is None:
        return data
    anchors, members, files, state, proof = result
    metadata = [dict(data), anchors, members, pool, collection.matches, collection.recall_audit]
    if not bounded_binding_parts(metadata, files, state, proof):
        return data
    bound = ValidationContext(deepcopy(dict(data)))
    bound._collection = collection; bound._log_capture = capture; bound._log_proof = proof
    bound._anchors = anchors; bound._members = members; bound._files = files; bound._state = state
    bound._pool = deepcopy(pool); bound._project = project; bound._root = Path(project.root).resolve()
    return issue(bound)


def log_receipt(data, entry, *, pending):
    seal = data._binding
    if (hasattr(data, '_no_logs') or type(seal) is not tuple or len(seal) != 2
            or type(seal[0]) is not str or seal[0] != 'validation-field-logs/v1'
            or type(seal[1]) is not str or len(seal[1]) != 64
            or any(c not in '0123456789abcdef' for c in seal[1])):
        return None
    current = log_binding(data)
    if snapshot(seal) != entry[1] or snapshot(current) != entry[1] or current != seal:
        return None
    if Path(data._project.root).resolve() != data._root:
        return None
    result = check(data._project, data.get('query'), data, data._pool,
                   data._collection, data._log_capture, pending=pending)
    if result is None:
        return None
    anchors, members, files, state, proof = result
    if (anchors != data._anchors or members != data._members or files != data._files
            or state != data._state or proof != data._log_proof):
        return None
    return data._anchors


def ordinary_enriched(data, path, freshness):
    baseline = dict(data); baseline['source_freshness'] = freshness
    handoff = baseline.get('query_handoff')
    if type(handoff) is dict:
        baseline['query_handoff'] = dict(handoff)
        baseline['query_handoff']['path_context'] = path
    return baseline


def enrich_logs(data, query, path, freshness):
    from .query_validation_field_selection import ValidationContext, issue, validation_field_receipt
    # Authenticated payload is finite before copying. A mutated oversized input
    # cannot receive private authority; caller returns its ordinary fallback.
    baseline = ordinary_enriched(data, path, freshness)
    if not preflight(data, data._pool, data._collection) or not preflight(baseline, data._pool, data._collection):
        return baseline
    baseline = deepcopy(baseline)
    if (validation_field_receipt(data, pending=True) is None or query != data.get('query')
            or snapshot(freshness) != snapshot(data.get('source_freshness'))
            or not preflight(baseline, data._pool, data._collection)
            or complete_candidate_rejections(data._project, query, data._collection,
                data._log_capture, baseline, data._pool)):
        return baseline
    result = ValidationContext(baseline)
    for field in ('_anchors', '_members', '_pool'):
        setattr(result, field, deepcopy(getattr(data, field)))
    for field in ('_root', '_files', '_state', '_project', '_collection', '_log_capture', '_log_proof'):
        setattr(result, field, getattr(data, field))
    return issue(result)
