"""English-only complete lifecycle source-set view over unchanged log context.

This is not log causality or unique ownership. Shared lifecycle/log guards,
source qualification and ordinary raw/accounting behavior remain unchanged.
"""
from copy import deepcopy
import math
from pathlib import Path

from .query_lifecycle_english_request import english_lifecycle_request
from .query_lifecycle_selection import LifecycleAuthority, LifecycleTrial, current_sources, snapshot
from .query_record_loop_selection import protected_record_loop

CODE_FIELDS = ('code_anchors', 'callable_evidence', 'source_excerpt_policy')
CALLABLE_KEYS = {'schema_version', 'certainty', 'primary', 'alternatives', 'boundary'}


class LifecycleLogContext(dict):
    def __copy__(self): return dict(self)
    def __deepcopy__(self, memo): return deepcopy(dict(self), memo)



def ordinary_callable(value):
    """Only known ordinary code-ranking structures are disposable code fields."""
    if (type(value) is not dict or not set(value) <= CALLABLE_KEYS
            or value.get('schema_version') != 'agent-callable-evidence/v1'
            or value.get('certainty') not in {'unavailable', 'uncertain', 'bounded'}
            or 'primary' not in value or type(value.get('alternatives')) is not list
            or len(value['alternatives']) > 2
            or ('boundary' in value and type(value['boundary']) is not str)):
        return False
    keys = {'file_path', 'symbol', 'owner_name', 'owner_kind', 'file_structural_coverage',
            'callable_roles', 'score', 'evidence_score', 'reasons', 'source_range'}
    for item in ([value['primary']] if value['primary'] is not None else []) + value['alternatives']:
        if (type(item) is not dict or not set(item) <= keys
                or not all(type(item.get(k)) is str and item[k] for k in ('file_path', 'symbol'))):
            return False
        for key in ('owner_name', 'owner_kind'):
            if key in item and type(item[key]) is not str: return False
        for key in ('callable_roles', 'reasons'):
            if key in item and (type(item[key]) is not list or not all(type(x) is str for x in item[key])): return False
        for key in ('score', 'evidence_score'):
            if key in item and (type(item[key]) not in (int, float) or not math.isfinite(item[key])): return False
        if 'file_structural_coverage' in item and (type(item['file_structural_coverage']) is not int or item['file_structural_coverage'] < 0): return False
        if 'source_range' in item:
            span = item['source_range']
            if (type(span) is not dict or not set(span) <= {'start_line', 'end_line', 'selection_reason'}
                    or type(span.get('start_line')) is not int or type(span.get('end_line')) is not int
                    or not 0 < span['start_line'] <= span['end_line']
                    or ('selection_reason' in span and type(span['selection_reason']) is not str)):
                return False
    return True


def binding(data):
    return (data.get('query'), snapshot(dict(data)), snapshot(data._pool),
            snapshot(data._authority._receipts), snapshot(data._trial))


def lifecycle_log_receipt(data, *, pending=False):
    if not isinstance(data, LifecycleLogContext): return None
    try:
        query = data.get('query'); authority = data._authority
        for context in (data, data._trial):
            handoff = context.get('query_handoff')
            if type(handoff) is not dict or ('path_context' in handoff and type(handoff['path_context']) is not dict):
                return None
        if (not english_lifecycle_request(query) or type(data._pool) is not list
                or not isinstance(authority, LifecycleAuthority)
                or data._binding != binding(data) or not authority.valid(query, data._pool)
                or not current_sources(authority)
                or not data['query_handoff']['log_anchors']
                or protected_record_loop(data, query, data._pool, pending=pending)
                or protected_record_loop(data._trial, query, data._pool, pending=True)):
            return None
        if (str(Path(data['project_path']).resolve()) != authority._root
                or data._trial.get('project_path') != data.get('project_path')
                or data._trial.get('project_id') != data.get('project_id')
                or data._trial.get('source_freshness') != data.get('source_freshness')
                or any(r['owner']['project_id'] != data.get('project_id') for r in authority._receipts)):
            return None
        freshness = data.get('source_freshness') or {}
        if (freshness.get('status') != 'current' or not 0 < len(authority._receipts) <= 3
                or any(r['owner']['index_generation'] != freshness.get('generation') for r in authority._receipts)):
            return None
        return authority
    except (AttributeError, KeyError, TypeError, ValueError, OSError):
        return None


def bind_lifecycle_log_context(query, baseline, trial):
    """Only called after the ordinary lifecycle binder declined its view."""
    try:
        authority = getattr(trial, '_lifecycle_authority', None)
        pool = getattr(trial, '_lifecycle_pool', None)
        if (not english_lifecycle_request(query) or query != baseline.get('query')
                or query != trial.get('query') or not isinstance(trial, LifecycleTrial)
                or not isinstance(authority, LifecycleAuthority) or type(pool) is not list
                or getattr(trial, '_lifecycle_pool_binding', None) != snapshot(pool)):
            return baseline
        result = LifecycleLogContext(baseline)
        result._authority = authority; result._pool = deepcopy(pool); result._trial = deepcopy(dict(trial))
        result._binding = binding(result)
        return result if lifecycle_log_receipt(result, pending=True) is not None else baseline
    except (AttributeError, KeyError, TypeError, ValueError, OSError):
        return baseline


def enrich_lifecycle_log_context(data, query, path, freshness):
    baseline = deepcopy(dict(data)); baseline['source_freshness'] = freshness
    baseline.setdefault('query_handoff', {})['path_context'] = deepcopy(path)
    if (lifecycle_log_receipt(data, pending=True) is None or query != data.get('query')
            or freshness != data.get('source_freshness')):
        return baseline
    result = LifecycleLogContext(baseline)
    result._authority = data._authority; result._pool = deepcopy(data._pool); result._trial = deepcopy(data._trial)
    result._binding = binding(result)
    return result if lifecycle_log_receipt(result) is not None else baseline


def compact_lifecycle_log_context(data, baseline):
    """All certified classes or the identical ordinary compact; never trim logs."""
    from .context_budget import synchronize_estimate
    from .context_compact import _compact_context
    from .performance_scoring import estimate_payload_tokens
    from .query_render_selection import complete_snapshot_projection
    authority = lifecycle_log_receipt(data)
    if authority is None: return baseline
    try:
        old = baseline['query_handoff'].get('callable_evidence')
        if not ordinary_callable(old): return baseline
        budget = baseline['output_budget']
        if (type(budget.get('target_tokens')) is not int or budget['target_tokens'] <= 0
                or type(budget.get('truncated')) is not bool
                or type(budget.get('estimated_tokens')) is not int or budget['estimated_tokens'] < 0):
            return baseline
        view = deepcopy(data._trial); anchors = []; receipts = []
        for receipt in authority._receipts:
            owner = receipt['owner']; path = receipt['path']
            anchors.append(dict(source='wiki', record_type='code_symbol', record_id=owner['id'],
                file_path=path, symbol=owner['symbol'], symbol_type='class',
                start_line=owner['start_line'], end_line=owner['end_line']))
            receipts.append((path, receipt['digest'], tuple(receipt['source'].splitlines()),
                             ((owner['symbol'], owner['start_line'], owner['end_line']),)))
        view['query_handoff']['code_anchors'] = anchors
        view['query_handoff']['callable_evidence'] = {
            'schema_version': 'agent-callable-evidence/v1', 'certainty': 'uncertain',
            'primary': None, 'alternatives': [],
            'boundary': 'finite_same_owner_source_shape_not_unique_owner_or_log_causality',
        }
        formatted = _compact_context(view, lifecycle_receipts=tuple(receipts))
        if (not complete_snapshot_projection(formatted, tuple(receipts))
                or len(formatted['query_handoff']['code_anchors']) != len(receipts)
                or {a['file_path'] for a in formatted['query_handoff']['code_anchors']} != {r[0] for r in receipts}):
            return baseline
        candidate = deepcopy(baseline)
        for key in CODE_FIELDS:
            candidate['query_handoff'][key] = deepcopy(formatted['query_handoff'][key])
        synchronize_estimate(candidate)
        if (estimate_payload_tokens(candidate) > min(1500, budget['target_tokens'])
                or candidate['output_budget']['estimated_tokens'] != estimate_payload_tokens(candidate)):
            return baseline
        restored = deepcopy(candidate)
        for key in CODE_FIELDS:
            if key in baseline['query_handoff']:
                restored['query_handoff'][key] = deepcopy(baseline['query_handoff'][key])
            else: restored['query_handoff'].pop(key, None)
        restored['output_budget']['estimated_tokens'] = baseline['output_budget']['estimated_tokens']
        if restored != baseline: return baseline
        return candidate
    except (AttributeError, KeyError, TypeError, ValueError, OSError, OverflowError):
        return baseline
