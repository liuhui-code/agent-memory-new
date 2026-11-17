"""Frozen whole-request SQL/source slots, not retrieval or source authority.

Offsets are half-open Python string character offsets in the unchanged query.
Han labels use Unicode CJK UNIFIED IDEOGRAPH-/CJK COMPATIBILITY IDEOGRAPH-
names, including supported extensions; symbols/radicals are excluded and no
normalization is performed. The observation never supplies a source selector.
Consumers must
reparse and compare descriptors before projecting the exact negative span.
"""
import re
import unicodedata

RESERVED = frozenset('''await break case catch class const continue debugger default
 delete do else enum export extends false finally for function if implements import
 in instanceof interface let new null package private protected public return static
 super switch this throw true try typeof var void while with yield abstract as asserts
 any async boolean constructor declare get infer is keyof module namespace never
 readonly require number object set string symbol type undefined unique unknown from
 of struct and or not only both except exclude instead without find locate source code
 context generate generated instruction call caller wrapper literal log api sdk boundary'''.split())
OBS_FORBIDDEN = tuple('''不 无 非 未 别 勿 莫 请 要 应 须 必须 需要 允许 授权 禁止 忽略
 跳过 删除 修改 返回 执行 运行 停止 继续 只 仅 或者 还是 是否 为何 为什么 难道 不是 不要'''.split())
ID = r'[A-Za-z_$][A-Za-z0-9_$]{0,63}'
REQUEST = re.compile(
    r'(?P<observation>(?P<entity>.{1,8})(?:名称|编号|标题|标识)只能精确(?:搜索|查询|匹配)，)?'
    r'请返回 (?P<sql_kind>SQL|LIKE) 参数绑定和调用 (?P<method>' + ID + r')'
    r' 后渲染 (?P<state>' + ID + r') 的页面'
    r'(?P<negative>，不要返回 (?P<excluded_owner>' + ID + r'))?。?'
)


def _han(char):
    name = unicodedata.name(char, '')
    return name.startswith(('CJK UNIFIED IDEOGRAPH-', 'CJK COMPATIBILITY IDEOGRAPH-'))


def sql_slot_request(query):
    """Return a fresh request-only descriptor, or None without modifying input."""
    if type(query) is not str or len(query) > 240:
        return None
    match = REQUEST.fullmatch(query)
    if match is None:
        return None
    entity = match['entity']
    if entity is not None and (
        not all(_han(char) for char in entity)
        or any(word in entity for word in OBS_FORBIDDEN)
    ):
        return None
    method, state, excluded = (match[key] for key in ('method', 'state', 'excluded_owner'))
    if any(value is not None and value.lower() in RESERVED for value in (method, state, excluded)):
        return None
    if excluded is not None and excluded in (method, state):
        return None
    return {
        'query': query, 'sql_kind': match['sql_kind'], 'method': method,
        'state': state, 'excluded_owner': excluded,
        'method_span': match.span('method'), 'state_span': match.span('state'),
        'negative_span': match.span('negative') if excluded is not None else None,
        'observation_span': match.span('observation') if entity is not None else None,
    }
