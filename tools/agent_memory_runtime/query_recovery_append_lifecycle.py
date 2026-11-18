# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Exact originating/selected/facade identities; no source reads or accounting."""
from copy import deepcopy
import json
import weakref
import sys
from .query_recovery_append_capture import current, seal
from .query_validation_log_capture import bounded_metadata

_live = {}


class RecoveryAppendPending(dict):
    pass


def _entry(data, phase):
    if type(data) is not RecoveryAppendPending:
        return None
    entry = _live.get(id(data))
    if (entry is None or entry['ref']() is not data or entry['phase'] != phase
            or seal(dict(data)) != entry['seal']
            or current(entry['project'], entry['query'], entry['collection']) is not entry['capture']):
        return None
    return entry


def pending(project, query, data, pool, collection):
    from .query_results import _context_pass
    caller = sys._getframe(1)
    if (caller.f_code is not _context_pass.__code__ or caller.f_locals.get('context') is not data
            or caller.f_locals.get('collection') is not collection
            or caller.f_locals.get('project') is not project or caller.f_locals.get('query') != query
            or (caller.f_locals.get('gated') or {}).get('matches', {}).get('wiki_matches') is not pool):
        return data
    try:
        if type(data) is not dict or type(pool) is not list or type(data.get('query_handoff')) is not dict:
            return data
        capture = current(project, query, collection)
        if capture is None or capture['origin_pass'] != id(caller) or data.get('query') != query or data.get('project_id') != project.project_id:
            return data
        if not bounded_metadata([data, pool, collection.matches, collection.recall_audit, capture['inventory']]):
            return data
        result = RecoveryAppendPending(data)
        key = id(result)
        def retire(ref):
            entry = _live.get(key)
            if entry is not None and entry['ref'] is ref:
                _live.pop(key, None)
        _live[key] = {'ref': weakref.ref(result, retire), 'phase': 'pending', 'seal': seal(dict(result)),
                      'project': project, 'query': query, 'pool': deepcopy(pool),
                      'collection': collection, 'capture': capture}
        return result
    except (AttributeError, TypeError, ValueError, OSError, UnicodeError, OverflowError):
        return data


def selected(data):
    from .query_results import limited_context
    caller = sys._getframe(1)
    if caller.f_code is not limited_context.__code__ or caller.f_locals.get('result') is not data:
        return data
    entry = _entry(data, 'pending')
    if entry is not None:
        _live[id(data)] = {**entry, 'phase': 'selected'}
    return data


def begin_facade(data):
    from .context_facade import ContextFacade
    caller = sys._getframe(1)
    if caller.f_code is not ContextFacade.execute.__code__ or caller.f_locals.get('result') is not data:
        return None
    entry = _entry(data, 'selected')
    if entry is None:
        return None
    # JSON allocation follows the same exact-builtin finite seal traversal.
    return (entry, json.dumps(dict(data), ensure_ascii=False, allow_nan=False))


def finish_facade(data, ticket, freshness, path):
    from .context_facade import ContextFacade
    caller = sys._getframe(1)
    if (caller.f_code is not ContextFacade.execute.__code__ or caller.f_locals.get('result') is not data
            or caller.f_locals.get('freshness') is not freshness or caller.f_locals.get('path_payload') is not path):
        return data
    if ticket is None:
        return data
    try:
        old, encoded = ticket
        if _live.get(id(data)) is not old or old['ref']() is not data or old['phase'] != 'selected':
            return data
        _live.pop(id(data), None)  # Always revoke the prior phase, including rejection.
        expected = json.loads(encoded)
        expected['source_freshness'] = freshness
        expected['query_handoff']['path_context'] = path
        if not bounded_metadata([dict(data), expected]) or dict(data) != expected:
            return data
        if current(old['project'], old['query'], old['collection']) is not old['capture']:
            return data
        _live[id(data)] = {**old, 'phase': 'final', 'seal': seal(dict(data))}
    except (AttributeError, TypeError, ValueError, OSError, UnicodeError, OverflowError):
        _live.pop(id(data), None)
    return data


def final_entry(data):
    return _entry(data, 'final')
