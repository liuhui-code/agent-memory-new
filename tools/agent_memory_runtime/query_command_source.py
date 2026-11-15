# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Flat command initializer association only, not execution or nested identity."""
import re
from .ecma_callback_mask import callback_mask_lines
from .ecma_callable_ranges import property_callback_ranges, PROPERTY_CALLBACK_RE
from .context_callback_binding import binding_context_range, _pairs, _members

WORD=r'[A-Za-z]+(?: [A-Za-z]+){0,3}'
RESERVED=set('and or not only except exclude return locate source code caller wrapper'.split())
FORMS=[rf'Locate the menu command binding owner for (?P<label>{WORD})\.?',
 rf'Choosing (?P<label>{WORD}) starts {WORD} instead of {WORD}\. Locate the (?:UI )?menu command binding owner(?:, not {WORD} or its {WORD})?\.?']


def command_request(query):
    if not isinstance(query,str) or len(query)>400:return None
    for form in FORMS:
        m=re.fullmatch(form,query,re.I)
        if m and not set(m['label'].lower().split())&RESERVED:return m['label'].casefold()
    return None


def command_binding(source,label):
    """Exact scalar and callback in one flat array object; unsupported => None."""
    lines=source.splitlines();masked=callback_mask_lines(lines)
    if masked is None:return None
    raw='\n'.join(lines);mask='\n'.join(masked);pairs=_pairs(mask)
    if pairs is None:return None
    offsets=[0]
    for line in lines[:-1]:offsets.append(offsets[-1]+len(line)+1)
    matches=[]
    for callback in property_callback_ranges(lines):
        expanded=binding_context_range('.ets',lines,callback,40,1500)
        if expanded is None:continue
        header=PROPERTY_CALLBACK_RE.match(masked[callback['start_line']-1])
        if header is None:continue
        pos=offsets[callback['start_line']-1]+header.start(1)
        enclosing=[a for a,b in pairs.items()if mask[a]=='{' and a<pos<b]
        if not enclosing:continue
        opening=max(enclosing);closing=pairs[opening]
        parents=[a for a,b in pairs.items()if a<opening<b]
        if not parents or mask[max(parents)]!='[':continue
        found=[];callbacks=[];label_keys=[]
        for left,right in _members(mask,opening,closing,pairs):
            m=re.match(r'\s*([A-Za-z_$][\w$]*)\s*:',mask[left:right])
            if m is None:return None
            value=raw[left+m.end():right].strip()
            scalar=re.fullmatch(r"(['\"])([A-Za-z]+(?: [A-Za-z]+){0,3})\1",value)
            if scalar and scalar[2].casefold()==label:
                found.append(scalar[2]);label_keys.append(m[1])
            c=PROPERTY_CALLBACK_RE.match(mask[left:right])
            if c:
                body=left+c.end()-1;end=pairs.get(body)
                if end is None:return None
                # Direct syntactic callback association, not receiver resolution.
                if re.fullmatch(r'\s*(?:await\s+)?this(?:\.[A-Za-z_$][\w$]*)+\s*\(\s*\)\s*;?\s*',mask[body+1:end]) is None:
                    return None
                callbacks.append(c[1])
        if len(found)==1 and len(callbacks)==1:
            array=max(parents)
            if wired_consumer(mask,pairs,array,label_keys[0],callbacks[0]):
                matches.append((callback,expanded))
    return matches[0] if len(matches)==1 else None


def declared_owner(source,row):
    """Check the active source declaration corresponding to the indexed owner."""
    lines=source.splitlines();mask=callback_mask_lines(lines)
    if mask is None:return False
    start,end=row['start_line']-1,row['end_line']-1
    if not 0<=start<=end<len(lines):return False
    header=re.fullmatch(r'\s*(?:export\s+)?struct\s+([A-Za-z_$][\w$]*)\s*\{\s*',mask[start])
    if header is None or header[1]!=row['symbol']:return False
    text='\n'.join(mask);pairs=_pairs(text)
    if pairs is None:return False
    opening=sum(len(x)+1 for x in mask[:start])+mask[start].index('{')
    closing=pairs.get(opening)
    return closing is not None and text.count('\n',0,closing)==end


def wired_consumer(mask,pairs,array,label_key,callback_key):
    """Finite direct field array -> ForEach item -> Button/event wiring witness."""
    ancestors=[a for a,b in pairs.items()if a<array<b and mask[a]=='{']
    if not ancestors:return False
    owner=max(ancestors)
    # Array declaration must be a direct member of the active struct, not a
    # local array inside a method, nested object or inner closure.
    owner_line=mask[:owner].rsplit('\n',1)[-1]
    if re.fullmatch(r'\s*(?:export\s+)?struct\s+[A-Za-z_$][\w$]*\s*',owner_line)is None:return False
    prefix=mask[:array].rsplit('\n',1)[-1]
    field=re.fullmatch(r'\s*(?:private\s+)?([A-Za-z_$][\w$]*)(?:\s*:\s*[A-Za-z_$][\w$]*\[\])?\s*=\s*',prefix)
    if field is None:return False
    name=field[1];end=pairs[owner]
    body=mask[owner+1:end]
    if '\\' in mask or re.search(r'\bthis\b(?!\s*\.)',mask):return False
    if len(re.findall(r'\b'+re.escape(name)+r'\b',mask))!=2:return False
    if len(re.findall(r'\bbuild\b',mask))!=1:return False
    # Require the only active occurrences to be the witnessed built-in calls.
    # This deliberately rejects declarations/aliases/shadowed UI primitives.
    if any(len(re.findall(r'\b'+word+r'\b',mask))!=1 for word in ('Button','ForEach')):return False
    consumer=re.compile(r'ForEach\s*\(\s*this\.'+re.escape(name)+r'\s*,\s*\(\s*([A-Za-z_$][\w$]*)(?:\s*:\s*[A-Za-z_$][\w$]*)?\s*\)\s*=>\s*\{\s*Button\s*\(\s*\1\.'+re.escape(label_key)+r'\s*\)\s*\.onClick\s*\(\s*\1\.'+re.escape(callback_key)+r'\s*\)\s*;?\s*\}\s*\)')
    found=list(consumer.finditer(body))
    if len(found)!=1:return False
    # Reject explicit additional direct-field occurrences. This is a narrow
    # syntax guard, not an alias/value-flow or absence-of-mutation proof.
    if len(re.findall(r'\bthis\s*\.\s*'+re.escape(name)+r'\b',body))!=1:return False
    location=owner+1+found[0].start()
    blocks=[a for a,b in pairs.items()if mask[a]=='{' and a<location<b]
    # Require the consumer to occur in the owner's build method. Allow normal
    # Column/Row nesting but reject another named method or callback ancestor.
    for opening in sorted(blocks,reverse=True):
        header=mask[:opening].rsplit('\n',1)[-1].strip()
        if re.fullmatch(r'(?:Column|Row)\s*\(\s*\)',header):continue
        if re.fullmatch(r'build\s*\(\s*\)',header):
            parents=[a for a,b in pairs.items()if mask[a]=='{' and a<opening<b]
            if not parents or max(parents)!=owner:return False
            # Complete field initializer: the literal must terminate before the
            # direct build declaration, not feed a chain/operator/continuation.
            between=mask[pairs[array]+1:opening]
            if re.fullmatch(r'\s*;?\s*build\s*\(\s*\)\s*',between) is None:return False
            # Admit the complete build statement template, not a ForEach
            # substring within a property call, constructor or larger expression.
            before=mask[opening+1:location]
            after=mask[owner+1+found[0].end():pairs[opening]]
            prefix=r'\s*(?:(?:Column|Row)\s*\(\s*\)\s*\{\s*)*'
            for word in ('Column','Row'):
                if len(re.findall(r'\b'+word+r'\b',mask))!=len(re.findall(r'\b'+word+r'\b',before)):return False
            return re.fullmatch(prefix,before) is not None and re.fullmatch(r'\s*(?:}\s*)*',after) is not None
        return False
    return False
