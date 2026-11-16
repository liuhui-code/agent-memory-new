# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Closed table-view request; background never supplies a label or identity."""
import re
WORD=r'[A-Za-z]+'
NP=rf'{WORD}(?: {WORD}){{0,2}}'
ROLE=rf'(?:(?:{WORD} )?lifecycle code|transport infrastructure|presentation components)'
REQUEST=re.compile(rf'(?:The (?P<a>{NP}) menu entry invokes the (?P<b>{NP}) workflow; )?Return the UI action-to-method dispatch table(?: rather than (?P<first>{ROLE})(?: or (?P<second>{ROLE}))?)?\.?',re.I|re.ASCII)
RESERVED=set('and or not no never only except exclude without return show find locate source quoted literal both all'.split())


def command_table_request(query):
    if not isinstance(query,str) or len(query)>400:return False
    match=REQUEST.fullmatch(query)
    if match is None:return False
    if any(set((match[key]or'').casefold().split())&RESERVED for key in ('a','b','first','second')):return False
    return not (match['second'] and match['second'].casefold()==match['first'].casefold())
