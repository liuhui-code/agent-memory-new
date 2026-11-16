# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Only fixed request grammar tokens lack identity authority; free names do not."""
import re
from .query_command_table_request import command_table_request, REQUEST


def identity_references(query):
    if not command_table_request(query):return None
    match=REQUEST.fullmatch(query);references=[match[k]for k in ('a','b')if match[k]]
    for key in ('first','second'):
        role=match[key]
        if role and len(role.split())==3 and role.casefold().endswith(' lifecycle code'):
            references.append(role.split()[0])
    return tuple(references)


def protected_table_scope(data,query,pool,*,pending=False):
    from .log_event_identity import event_match
    from .query_log_owner_admission import independently_named_log_owner
    references=identity_references(query)
    if references is None:return True
    handoff=data.get('query_handoff');path=handoff.get('path_context')if isinstance(handoff,dict)else None
    if pending and path is None:path={'activated':False,'path_candidates':[]}
    if (not isinstance(path,dict)or type(path.get('activated'))is not bool
        or not isinstance(path.get('path_candidates'),list)):return True
    if any(path.get(k)for k in ('activated','wrapped_log_evidence','path_candidates','seeds')):return True
    for key in ('code_anchors','log_anchors'):
        if not isinstance(handoff.get(key),list):return True
        for item in handoff[key]:
            if not isinstance(item,dict):return True
            if any(item.get(k)for k in ('identity_match','log_identity_match','graph_neighbor','graph_relation')):return True
    # Full original query, never role-stripped, for real log obligations.
    for log in handoff['log_anchors']:
        if event_match(log,query)['priority']>0 or independently_named_log_owner(log,query):return True
    for row in pool:
        if not isinstance(row,dict):return True
        if any(row.get(k)for k in ('identity_match','log_identity_match','graph_neighbor','graph_relation')):return True
        for key in ('file_path','symbol','qualified_name','owner_name'):
            value=row.get(key)
            if isinstance(value,str)and value and any(re.search(r'(?<![\w$])'+re.escape(value)+r'(?![\w$])',text,re.I)for text in references):return True
    return False
