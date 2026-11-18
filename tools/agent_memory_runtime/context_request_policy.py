# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Explicit, request-local presentation limits; never evidence authority."""
from contextvars import ContextVar
from copy import deepcopy
from dataclasses import dataclass


@dataclass(frozen=True)
class Policy:
    budget: int = 1500
    preserve: bool = False


_policy = ContextVar('compact_request_policy', default=Policy())
_ordinary = ContextVar('compact_request_ordinary', default=False)
_protected = ContextVar('compact_request_protected', default=None)


class CompactRequestIncomplete(ValueError):
    def __init__(self, reason, required=None):
        self.payload = {'schema_version': 'agent-context-incomplete/v1', 'complete': False,
                        'reason': reason, 'target_tokens': current().budget,
                        'preserve_selected_source_anchors': current().preserve}
        if required is not None:
            self.payload['required_estimated_tokens'] = required
        super().__init__(reason)


def current():
    return _policy.get()


def validate(budget, preserve):
    if type(budget) is not int or budget not in (1500, 2000) or type(preserve) is not bool:
        raise ValueError('compact policy requires budget 1500 or 2000 and a boolean preserve flag')


def render(data, callback, dispatch, budget, preserve):
    validate(budget, preserve)
    token = _policy.set(Policy(budget, preserve))
    ordinary = _ordinary.set(False)
    protected = _protected.set(None)
    try:
        result = dispatch(data, callback)
        if budget != 1500 or preserve:
            actual = result.get('output_budget') or {}
            if actual.get('target_tokens') != budget:
                raise CompactRequestIncomplete('unsupported_route_budget')
        if preserve:
            if _protected.get() is None:
                raise CompactRequestIncomplete('unsupported_preservation_route')
            check(result, _protected.get())
        return result
    finally:
        _protected.reset(protected)
        _ordinary.reset(ordinary)
        _policy.reset(token)


def mark_ordinary():
    _ordinary.set(True)


GUARDED = ('correction_guards', 'semantic_patch_notes', 'blocked_memory_notes',
           'conflict_notes', 'source_freshness')


def capture(payload):
    if not current().preserve:
        return None
    if not _ordinary.get():
        raise CompactRequestIncomplete('unsupported_preservation_route')
    snapshot = deepcopy({'handoff': payload['query_handoff'],
                         'outer': {k: payload.get(k) for k in GUARDED}})
    _protected.set(snapshot)
    return snapshot


def enforce(payload, budget, **kwargs):
    from .context_budget import enforce_budget
    return False if current().preserve else enforce_budget(payload, budget, **kwargs)


def finalize(payload, budget, **kwargs):
    from .context_budget import finalize_budget, synchronize_estimate
    from .performance_scoring import estimate_payload_tokens
    if not current().preserve:
        return finalize_budget(payload, budget, **kwargs)
    payload['output_budget'] = {'target_tokens': budget, 'estimated_tokens': 0,
                                'truncated': bool(kwargs.get('truncated') or (payload.get('output_budget') or {}).get('truncated'))}
    synchronize_estimate(payload)
    if estimate_payload_tokens(payload) > budget:
        raise CompactRequestIncomplete('protected_evidence_exceeds_budget', estimate_payload_tokens(payload))


def check(payload, before):
    if before is None:
        return payload
    if {k: payload.get(k) for k in GUARDED} != before['outer']:
        raise CompactRequestIncomplete('protected_outer_evidence_changed')
    before = before['handoff']
    after = deepcopy(payload['query_handoff'])
    anchors = after.get('code_anchors', [])
    old = before.get('code_anchors', [])
    if len(anchors) != len(old):
        raise CompactRequestIncomplete('selected_anchor_changed')
    excerpts = []
    for anchor, original in zip(anchors, old):
        if 'source_excerpts' not in original:
            added = anchor.pop('source_excerpts', [])
            if type(added) is not list or any(not valid_excerpt(e) for e in added):
                raise CompactRequestIncomplete('invalid_source_excerpt')
            excerpts.extend(added)
    if 'source_excerpt_policy' not in before:
        policy = after.pop('source_excerpt_policy', None)
        expected = {'source': 'current_worktree', 'body_persisted': False,
                    'excerpt_count': len(excerpts),
                    'excerpt_chars': sum(len(e['content']) for e in excerpts)}
        if (excerpts and policy != expected) or (not excerpts and policy is not None):
            raise CompactRequestIncomplete('source_statistics_changed')
    if after != before:
        raise CompactRequestIncomplete('protected_evidence_changed')
    from .performance_scoring import estimate_payload_tokens
    if estimate_payload_tokens(payload) > current().budget:
        raise CompactRequestIncomplete('protected_evidence_exceeds_budget', estimate_payload_tokens(payload))
    return payload


def valid_excerpt(e):
    from .context_display_union import display_excerpt_metadata
    if type(e) is not dict:
        return False
    lo, hi = e.get('start_line'), e.get('end_line')
    if (e.get('source') != 'current_worktree' or type(lo) is not int
            or type(hi) is not int or not 0 < lo <= hi or hi-lo+1 > 40
            or type(e.get('content')) is not str or len(e['content']) > 1500
            or type(e.get('truncated')) is not bool
            or type(e.get('selection_reason')) is not str or not e['selection_reason']
            or e['content'].count('\n') != hi-lo):
        return False
    focus = e.get('focus_line')
    if focus is not None and (type(focus) is not int or focus <= 0):
        return False
    if 'constituent_ranges' in e:
        return display_excerpt_metadata(e).get('constituent_ranges') == e['constituent_ranges']
    return e.get('symbol') is None or type(e['symbol']) is str
