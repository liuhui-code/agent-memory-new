# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Budget optional source bodies in existing order without reducing evidence."""
from copy import deepcopy
from .context_budget import synchronize_estimate, trim_excerpt
from .performance_scoring import estimate_payload_tokens
from .context_request_policy import CompactRequestIncomplete


def fit(payload, anchor, excerpt, budget):
    prior = deepcopy(anchor.get('source_excerpts', []))
    trial = deepcopy(excerpt)
    for _ in range(8):
        anchor['source_excerpts'] = [*prior, trial]
        update_policy(payload)
        synchronize_estimate(payload)
        if estimate_payload_tokens(payload) <= budget:
            return True
        before = len(trial['content'])
        if not trim_excerpt(trial):
            break
        if len(trial['content']) >= before:
            raise CompactRequestIncomplete('source_trim_did_not_progress')
        payload['output_budget']['truncated'] = True
    if prior:
        anchor['source_excerpts'] = prior
    else:
        anchor.pop('source_excerpts', None)
    payload['output_budget']['truncated'] = True
    update_policy(payload)
    synchronize_estimate(payload)
    if estimate_payload_tokens(payload) > budget:
        raise CompactRequestIncomplete('protected_evidence_exceeds_budget', estimate_payload_tokens(payload))
    return False


def update_policy(payload):
    handoff = payload['query_handoff']
    excerpts = [e for a in handoff['code_anchors'] for e in a.get('source_excerpts', [])]
    if excerpts:
        handoff['source_excerpt_policy'] = {
            'source': 'current_worktree', 'body_persisted': False,
            'excerpt_count': len(excerpts),
            'excerpt_chars': sum(len(e['content']) for e in excerpts),
        }
    else:
        handoff.pop('source_excerpt_policy', None)


def attach(payload, project_path, budget):
    from . import context_source_excerpt as source
    root = source.resolved_root(project_path)
    if root is None:
        return 0
    remaining = source.MAX_TOTAL_EXCERPT_CHARS
    count = 0
    for anchor in source.primary_anchors(payload['query_handoff']):
        path = source.safe_source_path(root, anchor.get('file_path'))
        if path is None:
            continue
        allowance = source.MAX_EXCERPT_CHARS
        acquired = []
        for selected in source.selected_ranges(anchor, path, str(payload.get('query') or '')):
            cap = min(allowance, remaining)
            if cap < source.MIN_EXCERPT_CHARS or len(acquired) >= source.MAX_EXCERPTS_PER_ANCHOR:
                break
            excerpt = source.read_binding_excerpt(path, selected, cap)
            if not excerpt:
                continue
            used = len(excerpt['content'])
            if used > cap:
                raise CompactRequestIncomplete('source_read_exceeded_cap')
            remaining -= used
            allowance -= used
            if source.binding_context_covers(anchor.get('source_excerpts', []), excerpt):
                continue
            acquired.append(excerpt)
            if fit(payload, anchor, excerpt, budget):
                count += 1
        if remaining < source.MIN_EXCERPT_CHARS:
            break
    return count
