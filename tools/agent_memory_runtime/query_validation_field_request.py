# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Finite validation source-view permission; observations are not source facts."""
import re
from .text import identifier_parts

RESERVED = frozenset('''a an the this that these those it its my your their our and or not no only both
except exclude instead without return find locate source code owner context
generate generated instruction call caller wrapper literal log logger event api
import boundary path graph field validation stop dispatch implementation action
update state page component method class current required invalid error'''.split())
FIELDS = {'display name': ('display','name'), 'customer code': ('customer','code'),
          '显示名': ('display','name'), '客户编号': ('customer','code')}
EN_HEAD = re.compile(r'Locate the (display name|customer code|[a-z]{1,24}) validation-stop and dispatch source\.')
ZH_HEAD = re.compile(r'请定位(显示名|客户编号)校验中止和动作分发源码。')
EN_OBSERVATION = re.compile(r'A required ([a-z]{1,24}) field shows an error but the invalid update still submits\. Locate the validation-stop and dispatch owner\.')
ZH_OBSERVATION = re.compile(r'必填(显示名|客户编号)为空时提示错误但仍提交更新，请定位校验中止和动作分发源码。')
IDENTIFIER = re.compile(r'[A-Za-z_$][A-Za-z0-9_$]*')


def validation_field_request(query):
    """Do not normalize/strip or remove the observation from the original query."""
    if type(query) is not str or not 0 < len(query) <= 240 or any(c in query for c in '\r\n\t\"\'`'):
        return None
    matches=[]
    for grammar in (EN_HEAD,ZH_HEAD,EN_OBSERVATION,ZH_OBSERVATION):
        found=grammar.fullmatch(query)
        if found:
            value=found.group(1)
            if value in FIELDS:matches.append(dict(kind='field',value=FIELDS[value]))
            elif value not in RESERVED and re.fullmatch(r'[a-z]{1,24}',value):
                matches.append(dict(kind='domain',value=value))
    return matches[0] if len(matches)==1 else None


def parts(value):
    if type(value) is not str or IDENTIFIER.fullmatch(value) is None:return None
    # Shared identifier_parts omits an unsplit whole token, restore that case.
    return tuple(identifier_parts(value) or [value.casefold()])


def validation_field_matches(permission, owner, method, field):
    """Lexical same-owner/method domain or exact field; never business authority."""
    if type(permission)is not dict or set(permission)!={'kind','value'}:return False
    owner_parts,method_parts,field_parts=parts(owner),parts(method),parts(field)
    if not owner_parts or not method_parts or not field_parts:return False
    kind,value=permission['kind'],permission['value']
    if kind=='field':
        return type(value)is tuple and value in set(FIELDS.values()) and field_parts==value
    if kind=='domain':
        return (type(value)is str and re.fullmatch(r'[a-z]{1,24}',value)is not None
                and value not in RESERVED and (value in owner_parts or value in method_parts))
    return False
