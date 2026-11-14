# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Positive, non-exhaustive declaration selection for a bounded request surface."""
from copy import deepcopy
import hashlib
from pathlib import Path
import re
from .text import json_list

REQUEST = re.compile(
    r'(?i:find|locate|identify) (?i:the|a|an) (?:(?i:reusable|declared) )?'
    r'@?Builder(?: (?i:declaration|method|function))?'
    r'(?: that (?:sets|configures|arranges|renders) (?P<attributes>[a-z ,]+))?\.?')
RESERVED = set('a an the in on at from to into with without by for of as about over under within '
               'through between before after is are was were be been being can could would should '
               'will may might must not no never only except excluding both either neither or but '
               'that which who whose while when where why how if then else than rather instead'.split())
MARKER = 'builder_declaration_selection'
FIELDS = ('id', 'project_id', 'file_path', 'symbol', 'symbol_key', 'qualified_name',
          'start_line', 'end_line', 'source_digest', 'index_generation')


def declaration_request(query):
    if not isinstance(query, str):
        return False
    match = REQUEST.fullmatch(query.strip())
    if match is None:
        return False
    attributes = match['attributes']
    if attributes is None:
        return True
    if any(word in RESERVED for word in attributes.split()):
        return False
    parts = re.split(r',\s*| and ', attributes)
    return bool(parts) and all(re.fullmatch(r'[a-z]+(?: [a-z]+)?', part) for part in parts)


def identity(row):
    return tuple(row.get(key) for key in FIELDS)


def valid_identity(row, project):
    return (type(row.get('id')) is int and row['id'] > 0
            and type(row.get('start_line')) is int and type(row.get('end_line')) is int
            and 0 < row['start_line'] <= row['end_line']
            and type(row.get('index_generation')) is int and row['index_generation'] > 0
            and row.get('project_id') == project.project_id
            and all(isinstance(row.get(k), str) and row[k] for k in
                    ('file_path', 'symbol', 'symbol_key', 'qualified_name'))
            and re.fullmatch('[0-9a-f]{64}', str(row.get('source_digest') or '')) is not None
            and row.get('symbol_type') in {'function', 'method'}
            and row.get('evidence_class') in {'static', 'exact'}
            and Path(row['file_path']).suffix == '.ets'
            and str(row.get('semantic_adapter') or '').partition('@')[0] == 'arkts-static')


class BuilderLocalization(dict):
    pass


class BuilderEvidence(dict):
    def valid_for(self, query):
        return (getattr(self, '_query', None) == query and declaration_request(query)
                and getattr(self, '_binding', None) == evidence_binding(self))


def evidence_binding(value):
    return (deepcopy(value.get('primary')), deepcopy(value.get('alternatives')),
            deepcopy(value.get(MARKER)))


def bind_localization(project, query, ranked, selected, result):
    if not declaration_request(query):
        return result
    known = [row for row in ranked if 'arkts_builder' in json_list(row.get('callable_roles'))]
    if not known or any(not valid_identity(row, project) for row in known):
        return result
    unique = {}
    for row in known:
        key = (row['file_path'], row['symbol_key'])
        if key in unique and identity(unique[key]) != identity(row):
            return result
        unique[key] = row
    known = list(unique.values())
    # Existing compact source merging permits three ranges per file, four files.
    # Current callable selection is narrower: every positive must already survive.
    if (len(known) > 3 or len({r['file_path'] for r in known}) > 4
            or any(not any(identity(row) == identity(s) for s in selected) for row in known)):
        return result
    try:
        root = Path(project.root).resolve()
        snapshots = {}
        for row in known:
            path = (root / row['file_path']).resolve()
            if not path.is_relative_to(root):
                return result
            if path not in snapshots:
                with path.open('rb') as stream:
                    data = stream.read(2 * 1024 * 1024 + 1)
                if len(data) > 2 * 1024 * 1024:
                    return result
                snapshots[path] = hashlib.sha256(data).hexdigest()
            if snapshots[path] != row['source_digest']:
                return result
    except OSError:
        return result
    bound = BuilderLocalization(result)
    bound._query = query
    bound._rows = deepcopy(known)
    return bound


def project_builder_evidence(localization, evidence):
    if not isinstance(localization, BuilderLocalization):
        return evidence
    from .query_callable_evidence import compact_candidate
    candidates = localization.get('callable_candidates') or []
    members = []
    for row in localization._rows:
        found = [c for c in candidates if c.get('symbol_id') == row['id']
                 and all(c.get(k) == row[k] for k in ('file_path','symbol','start_line','end_line'))]
        if len(found) != 1:
            return evidence
        # The permission refers to the declared callable, not an inferred subwindow.
        window = {k: row[k] for k in ('file_path','symbol','start_line','end_line')}
        window.update(symbol_id=row['id'], selection_reason='builder_declaration_range')
        member = compact_candidate(found[0], [window])
        if not member.get('source_range'):
            return evidence
        members.append(member)
    if not members:
        return evidence
    result = BuilderEvidence(evidence)
    result.update(primary=members[0], alternatives=members[1:], certainty='uncertain')
    result[MARKER] = {'kind': 'positive_declared_builder', 'known_matches': len(members),
                      'scope': 'retrieved_candidates_non_exhaustive', 'behavior_certified': False}
    result._query = localization._query
    result._members = deepcopy(members)
    result._binding = evidence_binding(result)
    return result


def builder_anchors(anchors, evidence, path_activated, query):
    """Return None when this contract is absent; copied markers fail closed."""
    if not isinstance(evidence, dict) or MARKER not in evidence:
        return None
    if (not isinstance(evidence, BuilderEvidence) or not evidence.valid_for(query)
            or path_activated or any(a.get('graph_neighbor') or a.get('graph_relation')
                                    or a.get('identity_match') or a.get('log_identity_match')
                                    for a in anchors)):
        return anchors
    from .context_callable_focus import callable_anchor
    return [callable_anchor(member, None) for member in evidence._members]
