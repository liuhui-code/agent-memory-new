# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

"""Guarded source-operation precedence among the current callable candidates."""
import re
from pathlib import Path
from .query_behavior_concepts import behavior_marker_terms
from .query_language import positive_retrieval_query
from .query_target_scope import classify_target_scope
from .semantic_callable_profile import TARGET_CUE_RE
from .text import json_list

# These are intent vetoes, not retrieval terms or scoring features.
NON_SOURCE_TARGET = re.compile(r'\b(?:literal|literals|text|strings?|declarations?|metadata|manifest|settings)\b|字面量|字符串|声明|清单|设置|文本', re.I)


def certify_source_operation(items, query):
    for item in items:
        item.pop("source_operation_match", None)
    positive = positive_retrieval_query(query)
    targets = list(TARGET_CUE_RE.finditer(positive))
    if (not targets or re.search(r"[`\"']", positive)
            or classify_target_scope(positive).get('kind') == 'multiple'
            or NON_SOURCE_TARGET.search(positive[targets[-1].end():])):
        return
    if any(item.get('typed_contract_match') or item.get('explicit_owner_identity_match')
           or 'exact_symbol' in item.get('localization_reasons', []) for item in items):
        return
    expected = set(behavior_marker_terms(positive))
    supported = {'runtimecapability', 'persistenceread'}
    if not expected or not expected <= supported:
        return
    if any('source_operation_checked:v2.1' not in json_list(item.get('callable_roles'))
           or Path(str(item.get('file_path') or '')).suffix not in {'.ts', '.ets'}
           or str(item.get('semantic_adapter') or '').partition('@')[0] not in {'arkts-static', 'typescript-static'}
           for item in items):
        return
    if any(expected & {role.partition(':')[2] for role in json_list(item.get('callable_roles'))
                       if role.startswith('source_operation_unresolved:')} for item in items):
        return
    candidates = []
    for item in items:
        start, end = item.get('start_line'), item.get('end_line')
        if not (type(start) is int and type(end) is int and 0 < start <= end
                and item.get('symbol_key') and item.get('source_digest')
                and item.get('evidence_class') in {'static', 'exact'} and not item.get('graph_depth')):
            return
        roles = {role.partition(':')[2] for role in json_list(item.get('callable_roles'))
                 if role.startswith('source_operation:')}
        if expected <= roles:
            candidates.append(item)
    # Uniqueness is only within this valid, recalled candidate set.
    if len(candidates) == 1:
        candidates[0]['source_operation_match'] = True
