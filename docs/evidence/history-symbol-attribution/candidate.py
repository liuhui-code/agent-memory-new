# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Unvalidated finite hypothesis; expected historical-reference counterexample."""
import re
IDENT=r'[A-Za-z_$][A-Za-z0-9_$]*'
HISTORY=re.compile(r'\bafter an earlier (?P<identifier>'+IDENT+r') failed\b',re.I)
def history_only(symbol,query):
    if not isinstance(query,str)or not re.fullmatch(IDENT,symbol or ''):return False
    if any(c in query for c in '\'"`()[]{};\n\r'):return False
    matches=list(HISTORY.finditer(query))
    if len(matches)!=1:return False
    history=matches[0]
    if history['identifier'].casefold()!=symbol.casefold():return False
    ending=re.search(r'\.\s*(?:Find|Locate) (?P<request>[^.!?]+)\.?$',query,re.I)
    if ending is None:return False
    request=ending['request']
    if re.search(r'\b(?:it|its|this|that|these|those|both|and|or|not|literal|log)\b',request,re.I):return False
    statement=query[:ending.start()]
    masked=statement[:history.start()]+statement[history.end():]
    if history.start()==0:
        if not masked.startswith(','):return False
        action=masked[1:].strip()
    else:action=masked.strip()
    if not re.fullmatch(r'[A-Za-z]+ing\b[^.!?]*\bmust\b[^.!?]+',action,re.I):return False
    outside=query[:history.start()]+query[history.end():]
    return not re.search(r'(?<![\w$])'+re.escape(symbol)+r'(?![\w$])',outside,re.I)
