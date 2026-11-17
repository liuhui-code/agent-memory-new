"""Private complete-method view. Raw fields, retrieval and source rank are unchanged."""
from copy import deepcopy
from pathlib import Path
from .query_output_loop_selection import snapshot
from .query_sql_slot_request import sql_slot_request
from .query_sql_slot_guard import protected_sql_slot, ordinary_callable
from .query_sql_slot_qualify import qualify_sql_slot
from .query_sql_slot_snapshot import current_scope

_ISSUED = object()


class SqlSlotContext(dict):
    def __copy__(self): return dict(self)
    def __deepcopy__(self, memo): return deepcopy(dict(self), memo)


def binding(data):
    scope = data._qualified['scope']
    return (snapshot(dict(data)), snapshot(data._descriptor), snapshot(data._pool),
            snapshot(data._qualified['anchors']), snapshot(data._qualified['members']),
            snapshot({k: scope[k] for k in ('paths','sources','digests','identity')}),
            str(scope['root']), str(Path(scope['project'].root).resolve()), scope['project'].project_id)


def issue(baseline, descriptor, pool, qualified):
    data = SqlSlotContext(baseline)
    data._descriptor = deepcopy(descriptor)
    data._pool = deepcopy(pool)
    data._qualified = qualified
    data._issued = _ISSUED
    data._binding = binding(data)
    return data


def bind_sql_slot_context(project, query, baseline, pool):
    descriptor = sql_slot_request(query)
    if descriptor is None or protected_sql_slot(baseline, query, pool, descriptor, pending=True):
        return baseline
    qualified = qualify_sql_slot(project, descriptor, pool)
    if qualified is None: return baseline
    return issue(baseline, descriptor, pool, qualified)


def sql_slot_receipt(data, *, pending=False):
    if not isinstance(data, SqlSlotContext): return None
    try:
        if (data._issued is not _ISSUED or data._binding != binding(data)
                or sql_slot_request(data.get('query')) != data._descriptor
                or protected_sql_slot(data, data['query'], data._pool, data._descriptor, pending=pending)
                or not current_scope(data._qualified['scope'])):
            return None
        return data._qualified['anchors']
    except (AttributeError, KeyError, TypeError, ValueError, OSError):
        return None


def compact_sql_slot(data, baseline):
    from .context_record_loop_transaction import apply_record_loop_transaction
    anchors = sql_slot_receipt(data)
    freshness = data.get('source_freshness', {})
    if (anchors is None or freshness.get('status') != 'current'
            or any(r['index_generation'] != freshness.get('generation') for r in data._qualified['members'])
            or not ordinary_callable(baseline.get('query_handoff', {}).get('callable_evidence'))
            or protected_sql_slot(baseline, data['query'], data._pool, data._descriptor)):
        return baseline
    return apply_record_loop_transaction(baseline, anchors)


def enrich_sql_slot(data, query, path, freshness):
    baseline = deepcopy(dict(data))
    baseline['source_freshness'] = freshness
    baseline.setdefault('query_handoff', {})['path_context'] = path
    if (sql_slot_receipt(data, pending=True) is None or query != data.get('query')
            or freshness != data.get('source_freshness')
            or protected_sql_slot(baseline, query, data._pool, data._descriptor)):
        return baseline
    return issue(baseline, data._descriptor, data._pool, data._qualified)


def accounting_sql_slot(data):
    from .context_compact import _compact_context
    baseline = _compact_context(dict(data))
    if compact_sql_slot(data, baseline) is baseline: return data
    view = deepcopy(dict(data))
    view['wiki_matches'] = deepcopy(data._qualified['members'])
    view['query_handoff']['code_anchors'] = deepcopy(data._qualified['anchors'])
    return view
