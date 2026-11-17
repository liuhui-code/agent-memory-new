"""Bounded complete lexical declaration inventory; no body/type/SDK proof."""
from dataclasses import dataclass
import hashlib
import re
from .ui_divider_source import Token, Unknown, quoted, NAME, NUMBER, RESERVED

MAX_BYTES=2*1024*1024
MAX_TOKENS=200000
MAX_DEPTH=256
MAX_ENTRIES=4096
CRITICAL={'List','Axis','ForEach','ListItem','Text','Column','Row','Scroll','State','Component','Entry'}
DECLARATION_WORDS={'class','struct','interface','function','import','export','type','enum','namespace','module','require'}
OPERATORS=tuple(sorted(('===','!==','==','!=','<=','>=','=>','++','--','&&','||','??','?.','+=','-=','*=','%=','&=','|=','^=','<<','>>','>>>','<<=','>>=','>>>=','**','**=','&&=','||=','??=','+','-','*','%','&','|','^','~','!','<','>','=','?',':','.',',',';','@','(',')','[',']','{','}'),key=len,reverse=True))

@dataclass(frozen=True)
class Declaration:
    name:str
    kind:str
    start_line:int
    end_line:int
    start:int
    end:int
    body_start:int
    body_end:int

@dataclass(frozen=True)
class ImportBinding:
    local:str
    remote:str
    module:str
    form:str
    start_line:int
    end_line:int
    start:int
    end:int

@dataclass(frozen=True)
class Inventory:
    declarations:tuple
    imports:tuple
    source_digest:str
    byte_count:int
    token_count:int


def lex(source, *, allow_templates=False):
    tokens=[];pairs={};stack=[];i=0;line=1;interpolations=0;template_suffix=False
    if re.search(r'\r(?!\n)',source) or any(c in source for c in ('\u2028','\u2029')):raise Unknown('line separator')
    while i<len(source):
        c=source[i]
        if c in ' \t\r\n':line+=c=='\n';i+=1;continue
        if source.startswith('//',i):
            end=source.find('\n',i+2);i=len(source) if end<0 else end;continue
        if source.startswith('/*',i):
            end=source.find('*/',i+2)
            if end<0:raise Unknown('unclosed comment')
            line+=source[i:end+2].count('\n');i=end+2;continue
        if template_suffix:
            if c not in ';,)]}':raise Unknown('template continuation')
            template_suffix=False
        if c=='`':
            from .ui_vertical_templates import scan_template
            if not allow_templates or not tokens:raise Unknown('template unsupported')
            previous=tokens[-1]
            opener=(previous.kind=='punct' and previous.value in {'(', '=', ','})
            if previous.value==',' and previous.kind=='punct':
                opener=any(tokens[n].value=='(' for n in stack)
            opener=opener or (previous.kind=='name' and previous.value=='return' and previous.line==line)
            if not opener or not any(tokens[n].value=='{' for n in stack):raise Unknown('template opener')
            emitted,end,line,count=scan_template(source,i,line,len(stack),MAX_DEPTH,MAX_TOKENS-len(tokens),256-interpolations)
            offset=len(tokens);local_stack=[]
            for j,t in enumerate(emitted):
                if t.kind=='punct' and t.value=='(':local_stack.append(offset+j)
                elif t.kind=='punct' and t.value==')':pairs[local_stack.pop()]=offset+j
            tokens.extend(emitted);interpolations+=count;i=end;template_suffix=True;continue
        if c in "'\"":end,value=quoted(source,i);kind='string'
        elif NAME.match(source,i):
            m=NAME.match(source,i);end=m.end();value=m.group();kind='name'
        elif c.isascii() and c.isdigit():
            m=re.match(r'[0-9]+(?:\.[0-9]*)?',source[i:]);value=m.group();end=i+len(value);kind='number'
            if len(value)>32 or not NUMBER.fullmatch(value) or (end<len(source) and (source[end].isalnum() or source[end] in '_$')):raise Unknown('number')
        else:
            value=next((op for op in OPERATORS if source.startswith(op,i)),None)
            if value is None:raise Unknown('active unknown token')
            end=i+len(value);kind='punct'
        token=Token(kind,value,i,end,line)
        if kind=='punct':
            if value in ('(','[','{'):
                stack.append(len(tokens))
                if len(stack)>MAX_DEPTH:raise Unknown('depth limit')
            elif value in (')',']','}'):
                if not stack or tokens[stack[-1]].value!={')':'(',']':'[','}':'{'}[value]:raise Unknown('delimiter')
                pairs[stack.pop()]=len(tokens)
        tokens.append(token)
        if len(tokens)>MAX_TOKENS:raise Unknown('token limit')
        i=end
    if stack:raise Unknown('unclosed delimiters')
    return tokens,pairs

class Walker:
    def __init__(self,tokens,pairs):
        self.t=tokens;self.pairs=pairs;self.i=0;self.names=set();self.declarations=[];self.imports=[]

    def at(self,value):
        return self.i<len(self.t) and self.t[self.i].kind!='string' and self.t[self.i].value==value

    def eat(self,value):
        if not self.at(value):raise Unknown('expected '+value)
        t=self.t[self.i];self.i+=1;return t

    def opt(self,value):
        if self.at(value):self.i+=1;return True
        return False

    def name(self):
        if self.i>=len(self.t):raise Unknown('name')
        t=self.t[self.i]
        if t.kind!='name' or t.value in RESERVED:raise Unknown('reserved/nonname')
        self.i+=1;return t.value

    def add_name(self,name):
        if name in self.names:raise Unknown('duplicate binding')
        self.names.add(name)
        if len(self.names)>MAX_ENTRIES:raise Unknown('entry limit')

    def decorator(self):
        self.eat('@');self.name()
        if self.at('.') or self.at('(') or self.at('?.'):raise Unknown('decorator payload')

    def import_header(self):
        first=self.eat('import');bindings=[]
        if self.opt('{'):
            remote=self.name();local=self.name() if self.opt('as') else remote
            bindings.append((local,remote))
            while self.opt(','):
                if self.at('}'):break
                remote=self.name();local=self.name() if self.opt('as') else remote
                bindings.append((local,remote))
            self.eat('}');form='named'
        elif self.opt('*'):
            self.eat('as');bindings.append((self.name(),'*'));form='namespace'
        else:bindings.append((self.name(),'default'));form='default'
        self.eat('from')
        if self.i>=len(self.t) or self.t[self.i].kind!='string':raise Unknown('module literal')
        last=self.t[self.i];module=last.value;self.i+=1
        if self.opt(';'):last=self.t[self.i-1]
        elif self.i<len(self.t):
            following=self.t[self.i]
            if following.line<=last.line or not (self.at('@') or following.kind=='name' and following.value in {'export','class','struct','interface','import'}):raise Unknown('import termination')
        for local,remote in bindings:
            if local in CRITICAL:raise Unknown('critical import binding')
            self.add_name(local)
            self.imports.append(ImportBinding(local,remote,module,form,first.line,last.line,first.start,last.end))

    def body(self,start,end):
        i=start
        while i<end:
            token=self.t[i]
            if token.kind=='name' and token.value in DECLARATION_WORDS:raise Unknown('nested/ambiguous declaration word')
            if token.kind=='punct' and token.value=='@':
                if i+1>=end or self.t[i+1].kind!='name' or self.t[i+1].value in RESERVED:raise Unknown('body decorator')
                if i+2<end and self.t[i+2].value in {'.','(','?.'} and self.t[i+2].kind=='punct':raise Unknown('body decorator payload')
            i+=1

    def run(self):
        while self.i<len(self.t):
            if self.at('import'):self.import_header();continue
            while self.at('@'):self.decorator()
            self.opt('export')
            if self.i>=len(self.t):raise Unknown('declaration')
            first=self.t[self.i]
            if first.kind!='name' or first.value not in {'class','struct','interface'}:raise Unknown('unsupported declaration')
            self.i+=1;name=self.name();self.add_name(name)
            opening=self.i;self.eat('{');closing=self.pairs[opening]
            self.body(self.i,closing);last=self.t[closing];self.i=closing+1
            self.declarations.append(Declaration(name,first.value,first.line,last.line,first.start,last.end,self.t[opening].start,last.end))
        return tuple(self.declarations),tuple(self.imports)


def inventory_vertical_file(source, *, allow_templates=False):
    try:
        if type(source)is not str or type(allow_templates)is not bool:return None
        raw=source.encode('utf-8')
        if len(raw)>MAX_BYTES:return None
        tokens,pairs=lex(source,allow_templates=allow_templates);declarations,imports=Walker(tokens,pairs).run()
        return Inventory(declarations,imports,hashlib.sha256(raw).hexdigest(),len(raw),len(tokens))
    except (Unknown,ValueError,TypeError,IndexError,KeyError,UnicodeError,RecursionError):return None
