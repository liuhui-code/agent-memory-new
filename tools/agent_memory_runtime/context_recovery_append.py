# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Append-only terminal transaction; ordinary accounting never enters here."""
from copy import deepcopy
import sqlite3
import sys
from .query_recovery_append_lifecycle import final_entry
from .query_recovery_append_capture import seal
from .query_validation_log_capture import bounded_metadata

_renders = {}


def _candidate(baseline, roots):
    from .context_compact import compact_code_anchor
    from .context_budget import synchronize_estimate
    if type(baseline) is not dict or type(roots) is not list or not bounded_metadata([baseline, roots]):
        return None
    handoff = baseline.get('query_handoff')
    if type(handoff) is not dict or type(handoff.get('code_anchors')) is not list:
        return None
    policy = handoff.get('source_excerpt_policy')
    if (type(policy) is not dict or set(policy) != {'source', 'body_persisted', 'excerpt_count', 'excerpt_chars'}
            or policy['source'] != 'current_worktree' or policy['body_persisted'] is not False):
        return None
    existing = handoff['code_anchors']
    excerpts = [e for a in existing for e in a.get('source_excerpts', [])]
    if (type(policy['excerpt_count']) is not int or type(policy['excerpt_chars']) is not int
            or policy['excerpt_count'] != len(excerpts)
            or policy['excerpt_chars'] != sum(len(e['content']) for e in excerpts)):
        return None
    additions = []
    for root in roots:
        anchor, excerpt = root['anchor'], root['excerpt']
        same_path = [a for a in existing if a.get('file_path') == anchor['file_path']]
        if same_path:
            if (len(same_path) != 1 or same_path[0].get('symbol') != anchor['symbol']
                    or not any(all(e.get(k) == excerpt[k] for k in ('symbol', 'start_line', 'end_line', 'content', 'truncated'))
                               for e in same_path[0].get('source_excerpts', []))):
                return None
            continue
        new = compact_code_anchor(anchor)
        new['source_excerpts'] = [deepcopy(excerpt)]
        additions.append(new)
    if not additions or len(existing) + len(additions) > 3:
        return None
    all_anchors = existing + additions
    all_excerpts = []
    for anchor in all_anchors:
        selected = anchor.get('source_excerpts', [])
        if type(selected) is not list or len(selected) > 2:
            return None
        for e in selected:
            if (type(e) is not dict or type(e.get('content')) is not str
                    or type(e.get('start_line')) is not int or type(e.get('end_line')) is not int
                    or not 1 <= e['end_line'] - e['start_line'] + 1 <= 40 or len(e['content']) > 1500):
                return None
            all_excerpts.append(e)
    chars = sum(len(e['content']) for e in all_excerpts)
    if chars > 2600 or not bounded_metadata([baseline, additions]):
        return None
    result = deepcopy(baseline)
    result['query_handoff']['code_anchors'].extend(additions)
    result['query_handoff']['source_excerpt_policy']['excerpt_count'] = len(all_excerpts)
    result['query_handoff']['source_excerpt_policy']['excerpt_chars'] = chars
    budget = result.get('output_budget')
    if type(budget) is not dict or type(budget.get('target_tokens')) is not int or budget['target_tokens'] <= 0:
        return None
    synchronize_estimate(result)
    if budget['estimated_tokens'] > min(1500, budget['target_tokens']):
        return None
    return result


def append_transaction(original, rendered, baseline, marker):
    issued = _renders.pop(marker, None)
    if issued is None or any(a is not b for a, b in zip(issued, (original, rendered, baseline))):
        return baseline
    try:
        entry = final_entry(original)
        if entry is None or seal(dict(original)) != seal(dict(rendered)):
            return baseline
        from .query_recovery_append_guard import admitted
        from .query_recovery_append_source import authenticate
        raw = dict(original)
        inventory = entry['capture']['inventory']
        collection = entry['collection']
        if not admitted(entry['query'], raw, entry['pool'], collection, inventory):
            return baseline
        proof = authenticate(entry['project'], entry['query'], raw, entry['pool'], inventory,
                             budget_context=[collection.matches, collection.recall_audit, baseline])
        if (proof is None or not bounded_metadata([raw, entry['pool'], collection.matches,
                collection.recall_audit, inventory, proof, baseline]) or final_entry(original) is not entry):
            return baseline
        result = _candidate(baseline, proof['roots'])
        if result is None or not bounded_metadata([raw, entry['pool'], collection.matches,
                collection.recall_audit, inventory, proof, baseline, result]):
            return baseline
        return result
    except (AttributeError, TypeError, ValueError, KeyError, IndexError, OSError, UnicodeError, OverflowError, sqlite3.Error):
        return baseline


def ordinary_render(original, rendered, callback, render_receipts):
    from .context_compact import _compact_context
    from .context_compact_dispatch import dispatch_compact_context
    # Keep the existing dispatcher callback contract (including the exact receipt object).
    baseline = callback(rendered, render_receipts)
    if (callback is not _compact_context or sys._getframe(1).f_code is not dispatch_compact_context.__code__
            or final_entry(original) is None):
        return baseline
    marker = object()
    _renders[marker] = (original, rendered, baseline)
    try:
        return append_transaction(original, rendered, baseline, marker)
    finally:
        _renders.pop(marker, None)
