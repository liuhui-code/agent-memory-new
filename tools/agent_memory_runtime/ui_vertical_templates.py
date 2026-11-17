"""Finite untagged template inventory scanner; never evaluates interpolation."""
import re
from .ui_divider_source import Token, Unknown, quoted, NAME, NUMBER, RESERVED

DECL_WORDS={'class','struct','interface','function','import','export','type','enum','namespace','module','require'}


def valid_expression(tokens):
    """E := ATOM | (E); no ignored tokens, calls, operators or indexing."""
    if not tokens:raise Unknown('empty interpolation')
    i=0;opens=0
    while i<len(tokens) and tokens[i].kind=='punct' and tokens[i].value=='(':
        i+=1;opens+=1
    if i>=len(tokens):raise Unknown('missing atom')
    t=tokens[i];i+=1
    if t.kind in {'string','number'}:pass
    elif t.kind=='name' and t.value in {'true','false','null'}:pass
    elif t.kind=='name' and (t.value=='this' or t.value not in RESERVED|DECL_WORDS):
        count=0
        while i<len(tokens) and tokens[i].kind=='punct' and tokens[i].value=='.':
            i+=1
            if i>=len(tokens) or tokens[i].kind!='name' or tokens[i].value in RESERVED|DECL_WORDS:raise Unknown('member identifier')
            i+=1;count+=1
        if t.value=='this' and not count:raise Unknown('standalone this')
    else:raise Unknown('unsupported atom')
    for _ in range(opens):
        if i>=len(tokens) or tokens[i].kind!='punct' or tokens[i].value!=')':raise Unknown('expression parens')
        i+=1
    if i!=len(tokens):raise Unknown('expression suffix')


def expression(source,i,line,depth,max_depth,token_budget):
    result=[];nest=0
    while i<len(source):
        c=source[i]
        if c in ' \t\r\n':line+=c=='\n';i+=1;continue
        if source.startswith('//',i):
            end=source.find('\n',i+2);i=len(source) if end<0 else end;continue
        if source.startswith('/*',i):
            end=source.find('*/',i+2)
            if end<0:raise Unknown('expression comment')
            line+=source[i:end+2].count('\n');i=end+2;continue
        if c=='}':
            if nest:raise Unknown('unclosed expression parens')
            valid_expression(result)
            return result,i,line
        if c in "'\"":end,value=quoted(source,i);kind='string'
        elif NAME.match(source,i):
            m=NAME.match(source,i);end=m.end();value=m.group();kind='name'
        elif c.isascii() and c.isdigit():
            m=re.match(r'[0-9]+(?:\.[0-9]*)?',source[i:]);value=m.group();end=i+len(value);kind='number'
            if len(value)>32 or not NUMBER.fullmatch(value) or (end<len(source) and (source[end].isalnum() or source[end] in '_$')):raise Unknown('expression number')
        elif c in '().':
            kind='punct';value=c;end=i+1
            if c=='(':
                nest+=1
                if depth+nest>max_depth:raise Unknown('template depth')
            elif c==')':
                nest-=1
                if nest<0:raise Unknown('expression close')
        else:raise Unknown('unsupported interpolation token')
        result.append(Token(kind,value,i,end,line));i=end
        if len(result)>token_budget:raise Unknown('template token budget')
    raise Unknown('unclosed interpolation')


def scan_template(source,start,line,base_depth,max_depth,token_budget,remaining_interpolations):
    if base_depth+1>max_depth:raise Unknown('template depth')
    result=[Token('template_open','`',start,start+1,line)]
    i=start+1;raw_start=i;raw_line=line;count=0
    def raw(end):
        if end>raw_start:result.append(Token('template_raw',source[raw_start:end],raw_start,end,raw_line))
    while i<len(source):
        c=source[i]
        if c=='`':
            raw(i);result.append(Token('template_close','`',i,i+1,line))
            if len(result)>token_budget:raise Unknown('template token budget')
            return result,i+1,line,count
        if source.startswith('${',i):
            raw(i);count+=1
            if count>remaining_interpolations or base_depth+2>max_depth:raise Unknown('template interpolation/depth limit')
            result.append(Token('interpolation_open','${',i,i+2,line))
            expr,end,line=expression(source,i+2,line,base_depth+2,max_depth,token_budget-len(result))
            result.extend(expr);result.append(Token('interpolation_close','}',end,end+1,line))
            if len(result)>token_budget:raise Unknown('template token budget')
            i=end+1;raw_start=i;raw_line=line;continue
        if c=='\\':
            i+=1
            if i>=len(source):raise Unknown('template escape end')
            escape=source[i]
            if escape in '\\`$nrtbfv':i+=1;continue
            if escape=='0' and (i+1==len(source) or not source[i+1].isdigit()):i+=1;continue
            width={'x':2,'u':4}.get(escape)
            if width and re.fullmatch('[0-9a-fA-F]{'+str(width)+'}',source[i+1:i+1+width]):i+=width+1;continue
            raise Unknown('unsupported template escape')
        if c=='\n':line+=1
        i+=1
    raise Unknown('unclosed template')
