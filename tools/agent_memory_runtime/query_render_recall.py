# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Finite lexical render-capability recall, never source-selection authority."""
from dataclasses import dataclass
import re
from . import query_builder_request as builder
from .query_language import positive_retrieval_query, excluded_code_candidate
from .query_method_evidence import method_evidence_focus_terms, METHOD_EVIDENCE_QUERY_TERM_LIMIT
from .text import unique_list, score_weighted_fields, weighted_token_matches

_NP=r'[A-Za-z]+(?: [A-Za-z]+){0,2}'
_PATTERN=re.compile(r'(?:(?P<observation>'+_NP+r') details still display markup tags\. )?'
    r'(?:Locate|Find|Return) the UI rendering cleanup owner'
    r'(?: rather than the (?P<exclusion>'+_NP+r') data entity)?\.?',re.I)
_RESERVED=set('and or not only except exclude return find locate source code render generate caller wrapper'.split())
_TERMS=('column','row','text')
_ISSUER=object()

@dataclass(frozen=True)
class RenderRequest:
    original: str
    observation: str
    exclusion: str


def parse_render_request(query):
    if not isinstance(query,str) or len(query)>400:
        return None
    match=_PATTERN.fullmatch(query)
    if match is None:
        return None
    if any(set((match[k] or '').lower().split())&_RESERVED for k in ('observation','exclusion')):
        return None
    return RenderRequest(query,match['observation'] or '',match['exclusion'] or '')

@dataclass(frozen=True)
class RenderRecall:
    request: RenderRequest
    retrieval: str
    terms: tuple[str,...]
    issuer: object

    def valid_for(self,query,original_query=None):
        return (self.issuer is _ISSUER and original_query==self.request.original
                and parse_render_request(original_query)==self.request
                and self.retrieval==query==positive_retrieval_query(original_query)
                and self.terms==_TERMS)

    def excludes(self,row):
        return excluded_code_candidate(self.request.original,dict(row))

    def __copy__(self):
        return RenderRecall(self.request,self.retrieval,self.terms,None)

    def __deepcopy__(self,memo):
        return self.__copy__()


def recall_projection(query,custom_port=None):
    old=builder.recall_projection(query,custom_port)
    if old is not None or custom_port is not None:
        return old
    request=parse_render_request(query)
    if request is None:
        return None
    retrieval=positive_retrieval_query(query)
    if len(unique_list([*method_evidence_focus_terms(retrieval),*_TERMS]))>METHOD_EVIDENCE_QUERY_TERM_LIMIT:
        return None
    return RenderRecall(request,retrieval,_TERMS,_ISSUER)


def projected_method_terms(query,projection,original_query=None,row=None):
    if not isinstance(projection,RenderRecall):
        return builder.projected_method_terms(query,projection,original_query,row)
    old=method_evidence_focus_terms(query)
    if not projection.valid_for(query,original_query) or (row is not None and projection.excludes(row)):
        return old
    merged=unique_list([*old,*projection.terms])
    return merged if len(merged)<=METHOD_EVIDENCE_QUERY_TERM_LIMIT else old


def score_projected_code(projection,row,original_query,query,tokens,expanded,fields,exact):
    if not isinstance(projection,RenderRecall):
        return builder.score_projected_code(projection,row,original_query,query,tokens,expanded,fields,exact)
    active=projection.valid_for(query,original_query) and not projection.excludes(row)
    added=[term for term in projection.terms if term not in tokens] if active else []
    score,reasons=score_weighted_fields(query,[*tokens,*added],expanded|set(added),fields,exact)
    matched=[term for term in added if any(weighted_token_matches(term,str(value).lower())for _,value,_ in fields)]
    return score,unique_list([*reasons,*['expanded_render_capability:'+term for term in matched]])


def filter_projected_method_ids(conn,project,ids,query,projection,original_query=None):
    if not isinstance(projection,RenderRecall):
        return builder.filter_projected_method_ids(conn,project,ids,query,projection,original_query)
    if not projection.valid_for(query,original_query) or not ids:
        return ids
    from .query_method_evidence import method_evidence_term_coverage
    rows=conn.execute('SELECT id,file_path,owner_name,method_evidence FROM code_symbols '
        'WHERE project_id=? AND id IN ('+','.join('?'for _ in ids)+')',[project.project_id,*ids]).fetchall()
    old=method_evidence_focus_terms(query)
    keep={row['id']for row in rows if not projection.excludes(row)
          or (len(old)>=2 and method_evidence_term_coverage(row['method_evidence']or'',old)>=2)}
    return [i for i in ids if i in keep]
