# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Terminal presentation only; caller supplies source-qualified bound anchors.

This module grants no request/source authority and performs no ranking, source
reads, narrowing or trimming. Failure returns the identical baseline object.
"""
from copy import deepcopy
import json

from .context_budget import synchronize_estimate
from .context_source_excerpt import (
    MAX_EXCERPT_ANCHORS, MAX_EXCERPTS_PER_ANCHOR, MAX_EXCERPT_LINES,
    MAX_EXCERPT_CHARS, MAX_TOTAL_EXCERPT_CHARS,
)
from .context_sufficiency import diagnosis_sufficiency
from .performance_scoring import estimate_payload_tokens

CODE_GAPS = {'no_code_anchor', 'limited_code_anchor_diversity'}
HANDOFF_KEYS = ('code_anchors', 'callable_evidence', 'source_excerpt_policy')
SUFFICIENCY_KEYS = ('status', 'next_action', 'reason_codes')
CALLABLE_KEYS = {'schema_version', 'certainty', 'primary', 'alternatives', 'boundary'}


def valid_anchors(anchors):
    if type(anchors) is not list or not 0 < len(anchors) <= MAX_EXCERPT_ANCHORS:
        return False
    chars = 0
    identities = set()
    for anchor in anchors:
        if type(anchor) is not dict or anchor.get('symbol_type') not in {'function', 'method'}:
            return False
        path, symbol = anchor.get('file_path'), anchor.get('symbol')
        if not isinstance(path, str) or not path or not isinstance(symbol, str) or not symbol:
            return False
        ids = anchor.get('record_ids')
        if type(ids) is not list or len(ids) != 1 or type(ids[0]) is not int or ids[0] <= 0:
            return False
        identity = (path, ids[0])
        if identity in identities:
            return False
        identities.add(identity)
        ranges, window, excerpts = (anchor.get(k) for k in ('source_ranges', 'read_window', 'source_excerpts'))
        if type(ranges) is not list or len(ranges) != 1 or type(ranges[0]) is not dict or type(window) is not dict:
            return False
        span = ranges[0]
        lo, hi = span.get('start_line'), span.get('end_line')
        if type(lo) is not int or type(hi) is not int or not 0 < lo <= hi:
            return False
        if span.get('symbol') != symbol or window.get('start_line') != lo or window.get('end_line') != hi:
            return False
        # Every qualified method is represented once, in its entirety.
        if type(excerpts) is not list or len(excerpts) != 1 or len(excerpts) > MAX_EXCERPTS_PER_ANCHOR:
            return False
        excerpt = excerpts[0]
        if type(excerpt) is not dict:
            return False
        if (excerpt.get('start_line'), excerpt.get('end_line'), excerpt.get('symbol')) != (lo, hi, symbol):
            return False
        content = excerpt.get('content')
        if (not isinstance(content, str) or not content or excerpt.get('truncated') is not False
                or excerpt.get('source') != 'validated_request_snapshot'):
            return False
        if hi - lo + 1 > MAX_EXCERPT_LINES or len(content.splitlines()) != hi - lo + 1:
            return False
        if len(content) > MAX_EXCERPT_CHARS:
            return False
        chars += len(content)
    return chars <= MAX_TOTAL_EXCERPT_CHARS


def restore_whitelist(candidate, baseline):
    """Restore allowed paths only, so all unrelated descendants are compared."""
    restored = deepcopy(candidate)
    for key in HANDOFF_KEYS:
        if key in baseline['query_handoff']:
            restored['query_handoff'][key] = deepcopy(baseline['query_handoff'][key])
        else:
            restored['query_handoff'].pop(key, None)
    restored['evidence_gaps'] = deepcopy(baseline['evidence_gaps'])
    for key in SUFFICIENCY_KEYS:
        restored['sufficiency'][key] = deepcopy(baseline['sufficiency'][key])
    restored['sufficiency']['coverage']['source_locatable_code_anchor'] = baseline['sufficiency']['coverage']['source_locatable_code_anchor']
    restored['output_budget']['estimated_tokens'] = baseline['output_budget']['estimated_tokens']
    return restored


def apply_record_loop_transaction(baseline, anchors):
    """Apply a complete code view atomically, never acquire its authority here."""
    try:
        if type(baseline) is not dict or not valid_anchors(anchors):
            return baseline
        json.dumps([baseline, anchors], allow_nan=False)
        handoff = baseline['query_handoff']
        old_callable = handoff.get('callable_evidence')
        if (type(handoff) is not dict or type(old_callable) is not dict
                or not set(old_callable) <= CALLABLE_KEYS):
            return baseline
        # Unknown/log-bearing callable containers are not disposable code fields.
        if any(key in json.dumps(old_callable) for key in ('"log_anchors"', '"path_context"', '"log_identity_match"')):
            return baseline
        budget = baseline['output_budget']
        if (type(budget.get('target_tokens')) is not int or budget['target_tokens'] <= 0
                or type(budget.get('truncated')) is not bool):
            return baseline
        if type(baseline['evidence_gaps']) is not list or not all(isinstance(x, str) for x in baseline['evidence_gaps']):
            return baseline
        candidate = deepcopy(baseline)
        current = candidate['query_handoff']
        current['code_anchors'] = deepcopy(anchors)
        current['callable_evidence'] = {
            'schema_version': 'agent-callable-evidence/v1', 'certainty': 'uncertain',
            'primary': None, 'alternatives': [],
            'boundary': 'positive_direct_syntax_not_unique_owner_or_runtime_causality',
        }
        policy = deepcopy(current.get('source_excerpt_policy', {}))
        if type(policy) is not dict:
            return baseline
        policy.update(source='validated_request_snapshot', body_persisted=False,
                      excerpt_count=len(anchors),
                      excerpt_chars=sum(len(a['source_excerpts'][0]['content']) for a in anchors))
        current['source_excerpt_policy'] = policy
        gaps = [x for x in baseline['evidence_gaps'] if x not in CODE_GAPS]
        if len({a['file_path'] for a in anchors}) < 3:
            gaps.append('limited_code_anchor_diversity')
        candidate['evidence_gaps'] = gaps
        recomputed = diagnosis_sufficiency(current, gaps, candidate.get('source_freshness'))
        old = baseline['sufficiency']
        if any(old['coverage'].get(k) != recomputed['coverage'][k] for k in ('log_anchor_count', 'path_candidate_count')):
            return baseline
        for key in SUFFICIENCY_KEYS:
            candidate['sufficiency'][key] = recomputed[key]
        candidate['sufficiency']['coverage']['source_locatable_code_anchor'] = recomputed['coverage']['source_locatable_code_anchor']
        synchronize_estimate(candidate)
        if estimate_payload_tokens(candidate) > min(1500, budget['target_tokens']):
            return baseline
        if candidate['output_budget']['estimated_tokens'] != estimate_payload_tokens(candidate):
            return baseline
        if restore_whitelist(candidate, baseline) != baseline:
            return baseline
        return candidate
    except (KeyError, TypeError, ValueError, OverflowError):
        return baseline
