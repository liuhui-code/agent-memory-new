# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Recovery-only same-collection direct-log facts, never serving authority."""
from copy import deepcopy
import hashlib
import json
import weakref
import sys
from .query_validation_log_capture import bounded_metadata, _direct_rows, _identity, _lane_identities
from .query_recovery_pair import recovery_request

_captures = {}


def seal(value):
    if not bounded_metadata(value):
        return None
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def capture(project, query, retrieval, collection, direct, effects):
    from .query_collect import collect_matches_with_audit
    from .query_results import _context_pass
    caller = sys._getframe(1)
    if (caller.f_code is not collect_matches_with_audit.__code__
            or caller.f_locals.get('collection') is not collection
            or caller.f_locals.get('project') is not project
            or caller.f_locals.get('query') != query
            or caller.f_locals.get('log_effects') is not effects
            or caller.f_locals.get('recalled') is None
            or caller.f_locals['recalled'].rows['code_log_statements'] is not direct):
        return
    producer = caller.f_back
    origin = id(producer) if producer and producer.f_code is _context_pass.__code__ else None
    key = id(collection)
    _captures.pop(key, None)
    from .query_collect import CollectedMatches
    from .query_language import positive_retrieval_query
    try:
        if (type(collection) is not CollectedMatches or not recovery_request(query)
                or retrieval != positive_retrieval_query(query)
                or type(direct) is not list or not 0 < len(direct) <= 64
                or type(effects) is not list or effects):
            return
        rows = _direct_rows(direct)
        identity = _identity(project, query, retrieval, collection)
        if rows is None or identity is None:
            return
        inventory = {'direct': rows, 'effects': []}
        state = [collection.matches, collection.recall_audit]
        if not _lane_identities(inventory) or not bounded_metadata([list(identity), inventory, state]):
            return
        frozen = deepcopy(inventory)
        def retire(ref):
            entry = _captures.get(key)
            if entry is not None and entry['ref'] is ref:
                _captures.pop(key, None)
        _captures[key] = {'ref': weakref.ref(collection, retire), 'identity': identity,
                          'inventory': frozen, 'inventory_seal': seal(frozen), 'state_seal': seal(state), 'origin_pass': origin}
    except (AttributeError, TypeError, ValueError, OSError, UnicodeError, OverflowError):
        return


def current(project, query, collection):
    from .query_language import positive_retrieval_query
    try:
        entry = _captures.get(id(collection))
        if (entry is None or entry['ref']() is not collection
                or _identity(project, query, positive_retrieval_query(query), collection) != entry['identity']
                or seal(entry['inventory']) != entry['inventory_seal']
                or seal([collection.matches, collection.recall_audit]) != entry['state_seal']):
            return None
        return entry
    except (AttributeError, TypeError, ValueError, OSError, UnicodeError, OverflowError):
        return None
