# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Bounded direct-call syntax witness; no receiver/effect or absence proof."""
from copy import deepcopy
import hashlib
from pathlib import Path
import re
from .ecma_callback_mask import callback_mask_lines
from .ecma_callable_headers import named_callable_header
from .ecma_callable_body import SIGNATURE_TOKENS
from .query_builder_request import parse_builder_request
from .text import identifier_tokens, tokenize, json_list

IDENT=re.compile(r'[A-Za-z_$][A-Za-z0-9_$]*')
RESERVED=set('if else for while do switch case default try catch finally with function class return throw new delete void typeof instanceof in of yield await import export const let var break continue debugger super this'.split())
PAIRS={'(':')','[':']','{':'}'}


def balanced_end(text,start):
    if start>=len(text) or text[start] not in PAIRS:
        return None
    stack=[]
    for i in range(start,len(text)):
        char=text[i]
        if char in PAIRS:
            stack.append(PAIRS[char])
        elif char in ')]}':
            if not stack or stack.pop()!=char:
                return None
            if not stack:
                return i+1
    return None


def whitespace(text,pos):
    start=pos
    while pos<len(text) and text[pos].isspace():
        pos+=1
    return pos,'\n' in text[start:pos]


def direct_chain_witness(data,row,requirements):
    try:
        text=data.decode('utf-8')
    except UnicodeDecodeError:
        return None
    lines=text.splitlines();masked=callback_mask_lines(lines)
    if masked is None:
        return None
    start=row['start_line']-1;end=row['end_line']-1
    if not 0<=start<=end<len(lines):
        return None
    raw='\n'.join(lines);code='\n'.join(masked)
    # Comments may be whitespace; top-level literals may not silently disappear.
    visible=list(code)
    for token in SIGNATURE_TOKENS.finditer(raw):
        if token.group().startswith(('"',"'",'`')):
            for i in range(token.start(),token.end()):
                if visible[i]!='\n':visible[i]='@'
    code=''.join(visible)
    stack=[]
    for char in code:
        if char in PAIRS:stack.append(PAIRS[char])
        elif char in ')]}':
            if not stack or stack.pop()!=char:return None
    if stack:return None
    header=named_callable_header(code.split('\n'),start)
    if header is None or header.name!=row['symbol'] or header.body_start is None:return None
    offset=sum(len(line)+1 for line in lines[:header.body_start[0]])+header.body_start[1]
    close=balanced_end(code,offset)
    if close is None or code.count('\n',0,close-1)!=end:return None
    tail=code[close:sum(len(x)+1 for x in lines[:end+1])-1]
    if tail.strip():return None
    body=code[offset+1:close-1];pos,_=whitespace(body,0);witnesses=[]
    while pos<len(body):
        match=IDENT.match(body,pos)
        if match is None or match.group() in RESERVED:return None
        pos,_=whitespace(body,match.end())
        if pos>=len(body) or body[pos]!='(':return None
        pos=balanced_end(body,pos)
        if pos is None:return None
        after,newline=whitespace(body,pos)
        if after<len(body) and body[after]=='{':
            pos=balanced_end(body,after)
            if pos is None:return None
        names=[]
        while True:
            after,newline=whitespace(body,pos)
            if after>=len(body) or body[after]!='.':break
            after,_=whitespace(body,after+1);match=IDENT.match(body,after)
            if match is None or match.group() in RESERVED:return None
            names.append(match.group());after,_=whitespace(body,match.end())
            if after>=len(body) or body[after]!='(':return None
            pos=balanced_end(body,after)
            if pos is None:return None
        if set(requirements)<=set(names):witnesses.append(tuple(names))
        if after>=len(body):break
        if body[after]==';':
            pos,_=whitespace(body,after+1)
        elif newline:pos=after
        else:return None
    return tuple(witnesses) if witnesses else None


def bind_modifier_localization(project,query,ranked,selected,result):
    request=parse_builder_request(query)
    if request is None:return result
    from .query_builder_selection import BuilderLocalization, identity, valid_identity
    known=[row for row in ranked if 'arkts_builder' in json_list(row.get('callable_roles'))]
    if not known or any(not valid_identity(row,project) for row in known):return result
    unique={}
    for row in known:
        key=(row['file_path'],row['symbol_key'])
        if key in unique and identity(unique[key])!=identity(row):return result
        unique[key]=row
    known=list(unique.values())
    if (len(known)>3 or any(not any(identity(row)==identity(s) for s in selected) for row in known)):
        return result
    snapshots={};members=[];proofs=[]
    try:
        root=Path(project.root).resolve()
        for row in known:
            path=(root/row['file_path']).resolve()
            if not path.is_relative_to(root):return result
            if path not in snapshots:
                with path.open('rb') as stream:data=stream.read(2*1024*1024+1)
                if len(data)>2*1024*1024:return result
                snapshots[path]=(data,hashlib.sha256(data).hexdigest())
            data,digest=snapshots[path]
            if digest!=row['source_digest']:return result
            owner=' '.join(str(row.get(k) or '') for k in ('file_path','owner_name'))
            if set([*identifier_tokens(owner),*tokenize(owner)])&set(request.exclusions):continue
            witness=direct_chain_witness(data,row,request.requirements)
            if witness:
                members.append(row);proofs.append((identity(row),witness))
    except (OSError,KeyError,TypeError,ValueError):return result
    if not members:return result
    bound=BuilderLocalization(result);bound._query=query;bound._rows=deepcopy(members)
    bound._modifier=(request,tuple(proofs))
    bound._snapshot=(query,deepcopy(members),deepcopy(bound._modifier))
    return bound
