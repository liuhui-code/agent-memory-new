"""Nonexclusive terminal body display; old hints and all old evidence retained."""
from copy import deepcopy
import sqlite3
from .context_graph_field_navigation import qualify_graph_field_navigation, _DisplayReceipt
from .context_graph_field_followup import append_graph_field_followup, _append_qualified_hints
from .context_budget import synchronize_estimate
from .performance_scoring import estimate_payload_tokens
from .validation_field_source import Unknown


def append_graph_field_display(project, original, payload, *, enabled=False):
    if (not enabled or type(payload) is not dict or type(payload.get('output_budget')) is not dict
        or payload['output_budget'].get('target_tokens') != 1500):
        return append_graph_field_followup(project, original, payload)
    baseline = payload
    try:
        receipt = qualify_graph_field_navigation(project, original, payload, _capture_body=True)
        if not isinstance(receipt, _DisplayReceipt):
            return payload
        baseline = _append_qualified_hints(payload, receipt.navigation)
        if (receipt.query != payload.get('query') or receipt.project_id != project.project_id
            or receipt.generation != payload['source_freshness']['generation'] or not receipt.bodies
            or len(receipt.navigation) != len(receipt.bodies)):
            return baseline
        anchors = baseline['query_handoff']['code_anchors']
        if len(anchors)+len(receipt.bodies)>5 or sum(a.get('role')=='expansion' for a in anchors)+len(receipt.bodies)>2:
            return baseline
        old_excerpts = []
        for anchor in anchors:
            if 'source_excerpt' in anchor or type(anchor.get('source_excerpts', [])) is not list:
                return baseline
            for excerpt in anchor.get('source_excerpts', []):
                if type(excerpt) is not dict or type(excerpt.get('content')) is not str:
                    return baseline
                old_excerpts.append(excerpt)
        policy = baseline['query_handoff'].get('source_excerpt_policy')
        if (type(policy) is not dict or policy.get('excerpt_count') != len(old_excerpts)
            or policy.get('excerpt_chars') != sum(len(e['content']) for e in old_excerpts)):
            return baseline
        trial = deepcopy(baseline)
        additions = deepcopy(receipt.navigation)
        for anchor, body in zip(additions, receipt.bodies):
            anchor['source_excerpts'] = [body]
        trial['query_handoff']['code_anchors'].extend(additions)
        excerpts = [e for a in trial['query_handoff']['code_anchors'] for e in a.get('source_excerpts', [])]
        chars = sum(len(e['content']) for e in excerpts)
        if chars>2600:
            return baseline
        trial['query_handoff']['source_excerpt_policy'].update(excerpt_count=len(excerpts), excerpt_chars=chars)
        synchronize_estimate(trial)
        return trial if estimate_payload_tokens(trial)<=1500 else baseline
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, AttributeError, sqlite3.Error, Unknown, RecursionError):
        return baseline
