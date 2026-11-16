# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Closed flat table + UI consumer certificate, not method/behavior resolution."""
import re
from .ecma_callback_mask import callback_mask_lines, quoted_end, comment_end, template_end
from .ecma_callable_ranges import property_callback_ranges, named_callable_ranges
from .context_callback_binding import _pairs
from .query_command_source import wired_consumer

NAME=r'[A-Za-z_$][A-Za-z0-9_$]*'
HEADER=re.compile(rf'\s*(?P<key>{NAME})\s*:\s*(?:(?P<async>async)[ \t]+)?\(\s*\)\s*(?::\s*(?:void|Promise\s*<\s*void\s*>))?\s*=>\s*\{{')
BODY=re.compile(rf'\s*(?P<await>await\s+)?this(?:\.{NAME})+\s*\(\s*\)\s*;?\s*')
LABEL=re.compile(r'''(['"])([A-Za-z]+(?: [A-Za-z]+){0,3})\1''')



def comment_only_mask(text):
    """Preserve every string token; only actual comments become whitespace."""
    chars=list(text);i=0
    while i<len(text):
        if text[i]in "'\"":
            i=quoted_end(text,i,text[i],len(text))
        elif text[i]=='`':
            i=template_end(text,i,len(text))
        elif text.startswith(('//','/*'),i):
            end=comment_end(text,i,len(text))
            if end is None:return None
            for j in range(i,end):
                if chars[j]!='\n':chars[j]=' '
            i=end
        else:i+=1
        if i is None:return None
    return ''.join(chars)



def direct_members(mask,syntax,opening,closing,pairs):
    """Structure from code mask, presence from literal-preserving lexical view."""
    result=[];start=index=opening+1
    while index<closing:
        if index in pairs:index=pairs[index]+1;continue
        if mask[index]==',':result.append((start,index));start=index+1
        index+=1
    if syntax[start:closing].strip():result.append((start,closing))
    return result


def complete_build(source,field,label,callback):
    # The structural mask proved balance; this view retains string literals so
    # quoted arguments/tails cannot masquerade as empty slots in that template.
    consumer=(rf'ForEach\s*\(\s*this\.{re.escape(field)}\s*,\s*\(\s*({NAME})'
              rf'(?:\s*:\s*{NAME})?\s*\)\s*=>\s*\{{\s*Button\s*\(\s*\1\.{re.escape(label)}'
              rf'\s*\)\s*\.onClick\s*\(\s*\1\.{re.escape(callback)}\s*\)\s*;?\s*\}}\s*\)')
    prefix=r'\s*build\s*\(\s*\)\s*\{\s*(?:(?:Column|Row)\s*\(\s*\)\s*\{\s*)*'
    return re.fullmatch(prefix+consumer+r'\s*(?:}\s*)+',source)is not None


def parse_command_table(source):
    """Return a whole-component certificate or None; caller retains unknowns."""
    lines=source.splitlines();masked=callback_mask_lines(lines)
    if masked is None:return None
    raw='\n'.join(lines);mask='\n'.join(masked);syntax=comment_only_mask(raw);pairs=_pairs(mask)
    if pairs is None or syntax is None:return None
    callbacks=property_callback_ranges(lines);named=named_callable_ranges(lines);tables=[]
    for array,close in pairs.items():
        if mask[array]!='[':continue
        entries=direct_members(mask,syntax,array,close,pairs)
        if not entries:continue
        found=[];keys=None;labels=set();bad=False
        for left,right in entries:
            start=left+len(mask[left:right])-len(mask[left:right].lstrip())
            if start>=right or mask[start]!='{' or pairs.get(start)!=right-1-len(mask[left:right])+len(mask[left:right].rstrip()):
                bad=True;break
            end=pairs[start]
            if syntax[left:start].strip() or syntax[end+1:right].strip():bad=True;break
            members=direct_members(mask,syntax,start,end,pairs)
            if len(members)!=2:bad=True;break
            label=None;callback=None;member_keys=set()
            for a,b in members:
                key=re.match(rf'\s*({NAME})\s*:',syntax[a:b])
                if key is None or key[1] in member_keys:bad=True;break
                member_keys.add(key[1]);value=syntax[a+key.end():b].strip();scalar=LABEL.fullmatch(value)
                if scalar:
                    if label is not None:bad=True;break
                    label=(key[1],scalar[2].casefold());continue
                header=HEADER.match(syntax[a:b])
                if header is None or callback is not None:bad=True;break
                opening=a+header.end()-1;closing=pairs.get(opening)
                if closing is None or syntax[closing+1:b].strip():bad=True;break
                body=BODY.fullmatch(syntax[opening+1:closing])
                if body is None or (body['await'] and not header['async']):bad=True;break
                key_pos=a+header.start('key');lo=mask.count('\n',0,key_pos)+1;hi=mask.count('\n',0,closing)+1
                matches=[c for c in callbacks if c['symbol']==key[1] and c['start_line']==lo and c['end_line']==hi]
                if len(matches)!=1:bad=True;break
                callback=matches[0]
            if bad or label is None or callback is None or label[1] in labels:bad=True;break
            labels.add(label[1]);current=(label[0],callback['symbol'])
            if keys is not None and keys!=current:bad=True;break
            keys=current;found.append(callback)
        if bad or not found or len({(c['symbol'],c['start_line'],c['end_line'])for c in found})!=len(found):continue
        if not wired_consumer(mask,pairs,array,*keys):continue
        field=re.fullmatch(rf'\s*(?:private\s+)?(?P<field>{NAME})(?:\s*:\s*{NAME}\[\])?\s*=\s*',syntax[:array].rsplit('\n',1)[-1])
        if field is None:continue
        ancestors=[a for a,b in pairs.items()if mask[a]=='{' and a<array<b];owner=max(ancestors)
        lo=mask.count('\n',0,owner)+1;hi=mask.count('\n',0,pairs[owner])+1
        declaration=re.fullmatch(rf'\s*(?:export\s+)?struct\s+({NAME})\s*\{{\s*',syntax.split('\n')[lo-1])
        builds=[b for b in named if b['symbol']=='build' and lo<b['start_line']<=b['end_line']<hi]
        if declaration is None or len(builds)!=1:continue
        build_offset=sum(len(line)+1 for line in lines[:builds[0]['start_line']-1])
        if re.fullmatch(r'\s*;?\s*',syntax[close+1:build_offset])is None:continue
        build_source='\n'.join(syntax.split('\n')[builds[0]['start_line']-1:builds[0]['end_line']])
        if not complete_build(build_source,field['field'],*keys):continue
        tables.append(dict(owner=declaration[1],start_line=lo,end_line=hi,callbacks=found,build=builds[0],array=array))
    if len(tables)!=1:return None
    result=tables[0];array=result.pop('array')
    # No second or unsupported array/access may hide alongside a known table.
    for a,b in pairs.items():
        if mask[a]!='[' or a==array:continue
        prefix=mask[:a].rsplit('\n',1)[-1]
        typed=re.fullmatch(rf'\s*(?:private\s+)?{NAME}\s*:\s*{NAME}',prefix)
        if not (typed and b==a+1 and a<array and re.fullmatch(r'\s*=\s*',mask[b+1:array])):return None
    return result


def possible_table(source):
    mask=callback_mask_lines(source.splitlines())
    return mask is None or '[' in '\n'.join(mask) or re.search(r'\bForEach\b','\n'.join(mask)) is not None
