"""Finite callable syntax hint, not iteration execution or numeric-type proof.

Only a complete simple method is admitted. A callback nested inside another
callback is not attributed to the method. Unknown syntax adds no evidence.
"""
import re

IDENT = r'[A-Za-z_$][A-Za-z0-9_$]*'
TYPE = IDENT + r'(?:\.' + IDENT + r')*'
HEAD = re.compile(r'\s*(?:(?:private|public|protected)\s+)?(?P<name>' + IDENT +
                  r')\s*\(\s*\)\s*(?::\s*void\s*)?\{(?P<body>[\s\S]*)\}\s*')
END = r'(?:[ \t]*;[ \t\n]*|[ \t]*\n[ \t\n]*)'
RESET = r'(?:this\.' + IDENT + r'[ \t]*=[ \t]*0' + END + r')*'
LOOP = re.compile(RESET + r'this\.(?P<collection>' + IDENT +
                  r')\.forEach\s*\(\s*\(\s*(?P<item>' + IDENT +
                  r')\s*(?::\s*' + TYPE + r'\s*)?\)[ \t]*=>\s*\{'
                  r'(?P<updates>[\s\S]*?)\}\s*\)\s*;?\s*')


def receiver_iteration_update(source, callable_name):
    if not isinstance(source, str) or len(source) > 12000:
        return False
    if any(c.isspace() and c not in ' \t\n' for c in source):
        return False
    # No lexical normalization that might turn comments/strings into operations.
    if any(c in source for c in ('/', "'", '"', '`', '\\', '\r', '\v', '\f', '\u2028', '\u2029')):
        return False
    method = HEAD.fullmatch(source)
    if method is None or method['name'] != callable_name:
        return False
    loop = LOOP.fullmatch(method['body'].strip())
    if loop is None:
        return False
    from .query_recovery_source import KEYWORDS
    if loop['item'] in KEYWORDS | {'this', 'super', 'of', 'in', 'await', 'yield'}:
        return False
    update = r'\s*this\.' + IDENT + r'\s*\+=\s*' + re.escape(loop['item']) + r'\.' + IDENT + r'[ \t]*'
    return re.fullmatch(r'(?:' + update + END + r')*(?:' + update + r';?[ \t\n]*)', loop['updates']) is not None


def receiver_iteration_terms(query):
    """Finite whole positive request; unknown modifiers never grant this hint."""
    if not isinstance(query, str) or len(query) > 360:
        return ()
    english = re.fullmatch(
        r"(?:find|locate|return) (?:the )?(?:state )?aggregation "
        r"(?:source|implementation) that accumulates (?:values|amounts|totals) "
        r"while iterating (?:records|items|entries)\.?", query.strip(), re.I)
    chinese = re.fullmatch(
        r"(?:请)?(?:定位|查找|返回)遍历(?:记录|条目|元素)时累加"
        r"(?:状态)?(?:总数|总额|数值)的(?:聚合)?(?:源码|实现)[。.]?", query.strip())
    return ('receiverfold',) if english or chinese else ()
