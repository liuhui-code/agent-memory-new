# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Keep log evidence without promoting weak matches over complete code evidence."""
import re
from .log_event_identity import event_match
from .query_behavior_concepts import behavior_marker_terms
from .query_target_scope import classify_target_scope, permits_cross_file_portfolio
from .text import tokenize


def admitted_log_owners(wiki, logs, query):
    expected = set(behavior_marker_terms(query))
    if len(expected) < 2 or permits_cross_file_portfolio(classify_target_scope(query)):
        return logs
    complete = any(
        item.get('kind') == 'symbol' and item.get('symbol_type') in {'function', 'method'}
        and expected <= set(tokenize(str(item.get('method_evidence') or '')))
        for item in wiki
    )
    if not complete:
        return logs
    independent = {(str(item.get('file_path') or ''), str(item.get('symbol') or '')) for item in wiki}
    return [item for item in logs if (
        not item.get('file_path') or not item.get('function')
        or (str(item.get('file_path') or ''), str(item.get('function') or '')) in independent
        or event_match(item, query)['priority'] > 0
        or independently_named_log_owner(item, query)
    )]


def independently_named_log_owner(item, query):
    if set(item.get('match_reasons') or []) & {'exact_function', 'exact_file_path', 'exact_identifier'}:
        return True
    path = str(item.get('file_path') or '')
    function = str(item.get('function') or '')
    # A qualified mention is sufficient to preserve, not proof of owner identity.
    return bool((path and path in query) or (function and re.search(
        r'\b[A-Za-z_$][\w$]*\.' + re.escape(function) + r'(?![\w$])', query)))
