# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Frozen pure helper experiment. No producer, index or serving mutation."""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from tools.agent_memory_runtime.query_behavior_concepts import behavior_marker_terms
from tools.agent_memory_runtime.query_language import positive_retrieval_query
from tools.agent_memory_runtime.query_target_scope import classify_target_scope
from tools.agent_memory_runtime.semantic_callable_profile import TARGET_CUE_RE
from tools.agent_memory_runtime.query_source_operation import NON_SOURCE_TARGET
from tools.agent_memory_runtime.query_definition_identity import explicit_owner_identity_match
from tools.agent_memory_runtime.query_typed_contract import classify_contract
from tools.agent_memory_runtime.text import query_tokens, score_weighted_fields

def gate(case):
    q = positive_retrieval_query(case['query'])
    targets = list(TARGET_CUE_RE.finditer(q))
    terms = query_tokens(q)
    markers = sorted(set(behavior_marker_terms(q)))
    exact = []
    for candidate in case['candidates']:
        _, reasons = score_weighted_fields(q, terms, set(terms), [], [('exact_symbol', candidate['symbol'], 12.0)])
        if 'exact_symbol' in reasons or explicit_owner_identity_match(q, candidate['owner_name']):
            exact.append(candidate)
    veto = {
        'no_target_cue': not targets,
        'quoted': bool(re.search(r"[`\"']", q)),
        'multiple': classify_target_scope(q).get('kind') == 'multiple',
        'non_source_target': bool(targets and NON_SOURCE_TARGET.search(q[targets[-1].end():])),
        'explicit_identity': bool(exact),
        'typed_request': bool(classify_contract(q)),
        'no_markers': not markers,
    }
    return {'admit': not any(veto.values()), 'markers': markers, 'vetoes': veto, 'positive_query': q}

if __name__ == '__main__':
    d = Path(__file__).parent
    p = json.loads((d / 'protocol.json').read_text())
    out = []
    for c in p['cases']:
        r = gate(c)
        out.append({'id': c['id'], 'query': c['query'], 'expected_admit': c['expected_admit'], 'observed': r, 'pass': r['admit'] == c['expected_admit']})
    (d / 'results.json').write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps({'cases': len(out), 'pass': sum(r['pass'] for r in out), 'failed': [r['id'] for r in out if not r['pass']]}, indent=2))
