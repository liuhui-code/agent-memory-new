"""Finite trial-only lexical discovery; never a source certificate."""
from dataclasses import dataclass
from . import query_render_recall as prior
from .query_language import positive_retrieval_query
from .query_method_evidence import method_evidence_focus_terms, METHOD_EVIDENCE_QUERY_TERM_LIMIT
from .text import unique_list, score_weighted_fields, weighted_token_matches

ISSUER = object()
TERMS = ('ontouch', 'touches')
RETRIEVAL = 'ontouch touches'

@dataclass(frozen=True)
class TouchRecall:
    original: str
    retrieval: str
    terms: tuple
    issuer: object
    def valid_for(self, query, original_query=None):
        from .query_touch_index_request import touch_index_request
        return (self.issuer is ISSUER and touch_index_request(self.original)
                and original_query == self.original
                and query == self.retrieval == RETRIEVAL
                and self.terms == TERMS)
    def __copy__(self): return TouchRecall(self.original, self.retrieval, self.terms, None)
    def __deepcopy__(self, memo): return self.__copy__()


def recall_projection(query, custom_port=None, allow_render_recall=False, *, allow_touch_recall=False):
    old = prior.recall_projection(query, custom_port, allow_render_recall)
    if old is not None or custom_port is not None or not allow_touch_recall:
        return old
    from .query_touch_index_request import touch_index_request
    if not touch_index_request(query): return None
    retrieval = RETRIEVAL
    if len(unique_list([*method_evidence_focus_terms(retrieval), *TERMS])) > METHOD_EVIDENCE_QUERY_TERM_LIMIT:
        return None
    return TouchRecall(query, retrieval, TERMS, ISSUER)


def projected_method_terms(query, projection, original_query=None, row=None):
    if not isinstance(projection, TouchRecall):
        return prior.projected_method_terms(query, projection, original_query, row)
    old = method_evidence_focus_terms(query)
    if not projection.valid_for(query, original_query): return old
    merged = unique_list([*old, *TERMS])
    return merged if len(merged) <= METHOD_EVIDENCE_QUERY_TERM_LIMIT else old


def score_projected_code(projection, row, original_query, query, tokens, expanded, fields, exact):
    if not isinstance(projection, TouchRecall):
        return prior.score_projected_code(projection, row, original_query, query, tokens, expanded, fields, exact)
    added = [t for t in TERMS if t not in tokens] if projection.valid_for(query, original_query) else []
    score, reasons = score_weighted_fields(query, [*tokens, *added], expanded | set(added), fields, exact)
    matched = [t for t in added if any(weighted_token_matches(t, str(v).lower()) for _, v, _ in fields)]
    return score, unique_list([*reasons, *['expanded_touch_index_capability:' + t for t in matched]])


def filter_projected_method_ids(conn, project, ids, query, projection, original_query=None):
    if isinstance(projection, TouchRecall): return ids
    return prior.filter_projected_method_ids(conn, project, ids, query, projection, original_query)


def projected_behavior_terms(query, projection, original_query=None):
    return prior.projected_behavior_terms(query, projection, original_query)
