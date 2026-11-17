"""Finite node-local explicit-axis configuration, not type or runtime proof."""
from .ui_divider_source import tokenize, Unknown, NAME, RESERVED, ParsedFrames

API = {'List','Axis','ForEach','ListItem','Text','Column','Row','Scroll','State','Component','Entry'}
PRIMITIVES = {'string','number','boolean'}

class Parser:
    def __init__(self, source):
        self.t,self.pairs=tokenize(source); self.i=0; self.names=set(); self.callback_names=set()

    def at(self,x):
        return self.i<len(self.t) and self.t[self.i].kind!='string' and self.t[self.i].value==x

    def eat(self,x):
        if not self.at(x): raise Unknown('expected '+x)
        t=self.t[self.i];self.i+=1;return t

    def opt(self,x):
        if self.at(x):self.i+=1;return True
        return False

    def name(self):
        if self.i>=len(self.t):raise Unknown('name')
        t=self.t[self.i]
        if t.kind!='name' or t.value in RESERVED|API:raise Unknown('binding/shadow')
        self.i+=1;return t.value

    def typ(self):
        if self.i<len(self.t) and self.t[self.i].kind=='name' and self.t[self.i].value in PRIMITIVES:
            x=self.t[self.i].value;self.i+=1;return x
        return self.name()

    def endstmt(self):
        if self.opt(';') or self.i==len(self.t) or self.at('}'):return
        if self.t[self.i].line>self.t[self.i-1].line:return
        raise Unknown('statement boundary')

    def literal(self,typ=None):
        if self.i>=len(self.t):raise Unknown('literal')
        t=self.t[self.i]
        actual=t.kind if t.kind in {'string','number'} else ('boolean' if t.kind=='name' and t.value in {'true','false'} else None)
        if actual is None or (typ is not None and typ!=actual):raise Unknown('literal type')
        self.i+=1;return t

    def parse(self,wanted):
        result={}
        while self.i<len(self.t):
            dec=[]
            while self.opt('@'):
                if self.at('Entry'):dec.append('Entry');self.i+=1
                elif self.at('Component'):dec.append('Component');self.i+=1
                else:raise Unknown('decorator')
            if len(set(dec))!=len(dec):raise Unknown('duplicate decorator')
            self.opt('export')
            if self.i>=len(self.t):raise Unknown('declaration')
            first=self.t[self.i]
            if first.kind!='name' or first.value not in {'struct','class','interface'}:raise Unknown('declaration kind')
            kind=first.value;self.i+=1;owner=self.name()
            if owner in self.names:raise Unknown('duplicate owner')
            self.names.add(owner);self.eat('{');fields={};members=set();build=None;sites=[];self.owner_callbacks=set()
            if dec and (kind!='struct' or 'Component' not in dec):raise Unknown('component decorators')
            while not self.at('}'):
                state=self.opt('@')
                if state:self.eat('State')
                if self.at('private') or self.at('public'):self.i+=1
                start=self.t[self.i] if self.i<len(self.t) else None
                if self.at('build'):self.i+=1;name='build'
                else:name=self.name()
                if name in members:raise Unknown('duplicate member')
                members.add(name)
                if self.opt(':'):
                    typ=self.typ();array=self.opt('[')
                    if array:self.eat(']')
                    if kind=='interface':
                        if state:raise Unknown('interface State')
                        self.endstmt();fields[name]=(typ,array);continue
                    self.eat('=')
                    if array:self.eat('[');self.eat(']')
                    else:self.literal(typ)
                    self.endstmt();fields[name]=(typ,array);continue
                if state or kind=='interface':raise Unknown('method kind')
                self.eat('(');self.eat(')')
                if name=='build':
                    if kind!='struct' or 'Component' not in dec:raise Unknown('build component')
                    self.eat('{');nodes=self.nodes(fields,None,False,0);last=self.eat('}')
                    build=(start,last);sites=self.list_sites(nodes) if owner in wanted else []
                else:
                    self.eat(':');typ=self.typ()
                    if typ not in PRIMITIVES:raise Unknown('auxiliary type')
                    self.eat('{');ret=self.eat('return');value=self.literal(typ)
                    if value.line!=ret.line:raise Unknown('return ASI')
                    self.endstmt();self.eat('}')
            last=self.eat('}')
            if self.owner_callbacks & set(fields):raise Unknown('callback own field shadow')
            if owner in wanted:
                if kind!='struct' or 'Component' not in dec or build is None:raise Unknown('wanted component')
                if len(sites)!=1 or not sites[0]['positive']:raise Unknown('unsupported wanted layout')
                result[owner]=dict(owner=owner,kind='struct',owner_start=first.line,owner_end=last.line,
                    owner_start_offset=first.start,owner_end_offset=last.end,
                    build_start=build[0].line,build_end=build[1].line,
                    build_start_offset=build[0].start,build_end_offset=build[1].end,positive=True,sites=sites)
        if self.callback_names & self.names:raise Unknown('callback declaration shadow')
        if set(result)!=wanted:raise Unknown('missing owner')
        return ParsedFrames(result,sorted(self.names))

    def nodes(self,fields,binding,in_item,depth):
        if depth>32:raise Unknown('nesting cap')
        result=[]
        while not self.at('}'):
            if self.i>=len(self.t):raise Unknown('node end')
            first=self.t[self.i]
            if self.opt('ForEach'):
                if binding is not None:raise Unknown('nested callback')
                self.eat('(');self.eat('this');self.eat('.');field=self.name()
                if field not in fields or not fields[field][1]:raise Unknown('collection binding')
                self.eat(',');callback_start=self.eat('(');param=self.name()
                if param in fields:raise Unknown('callback shadow')
                self.callback_names.add(param);self.owner_callbacks.add(param)
                self.eat(':');typ=self.typ()
                if typ!=fields[field][0]:raise Unknown('nominal mismatch')
                self.eat(')');self.eat('=>');self.eat('{')
                children=self.nodes(fields,(param,typ,field),False,depth+1)
                callback_end=self.eat('}');last=self.eat(')')
                node=dict(kind='ForEach',children=children,field=field,parameter=param,element_type=typ,
                          start_line=first.line,end_line=last.line,start_offset=first.start,end_offset=last.end,
                          callback_start_line=callback_start.line,callback_end_line=callback_end.line,
                          callback_start_offset=callback_start.start,callback_end_offset=callback_end.end)
            else:
                if first.kind!='name' or first.value not in {'Column','Row','List','ListItem','Text','Scroll'}:raise Unknown('node')
                kind=first.value;self.i+=1;self.eat('(');text=None;literal_text=False
                if kind=='Text':
                    if self.i<len(self.t) and self.t[self.i].kind in {'string','number'}:
                        self.literal();literal_text=True
                    elif binding and self.at(binding[0]):
                        self.i+=1;member=None
                        if binding[1] not in PRIMITIVES:self.eat('.');member=self.name()
                        text=dict(parameter=binding[0],member=member,field=binding[2],inside_list_item=in_item)
                    elif self.opt('this'):
                        self.eat('.');f=self.name()
                        if binding or f not in fields or fields[f][1]:raise Unknown('unbound Text')
                    else:raise Unknown('Text argument')
                self.eat(')');children=[]
                if kind!='Text':
                    self.eat('{');children=self.nodes(fields,binding,in_item or kind=='ListItem',depth+1);self.eat('}')
                node=dict(kind=kind,children=children,text=text,literal_text=literal_text,axis=None,start_line=first.line,start_offset=first.start)
                mods=set()
                while self.opt('.'):
                    if self.opt('listDirection'):
                        if kind!='List' or 'axis' in mods:raise Unknown('axis receiver/duplicate')
                        mods.add('axis');axis_start=self.t[self.i-1];self.eat('(');self.eat('Axis');self.eat('.')
                        if self.at('Vertical'):node['axis']='Vertical';self.i+=1
                        elif self.at('Horizontal'):node['axis']='Horizontal';self.i+=1
                        else:raise Unknown('axis value')
                        axis_end=self.eat(')');node['axis_range']=(axis_start.start,axis_end.end)
                    elif self.opt('height'):
                        if 'height' in mods:raise Unknown('height duplicate')
                        mods.add('height');self.eat('(')
                        if self.i>=len(self.t) or self.t[self.i].kind not in {'string','number'}:raise Unknown('height scalar')
                        self.literal();self.eat(')')
                    else:raise Unknown('modifier')
                node.update(end_line=self.t[self.i-1].line,end_offset=self.t[self.i-1].end)
            self.endstmt();result.append(node)
        return result

    def list_sites(self,nodes):
        def reject_literals(children):
            for n in children:
                if n.get('literal_text'):raise Unknown('unbound literal Text in wanted body')
                if n['kind']=='Scroll':raise Unknown('Scroll anywhere in wanted body')
                reject_literals(n['children'])
        reject_literals(nodes)
        sites=[]
        for node in nodes:
            if node['kind']=='List':
                callbacks=[]
                def find(children):
                    for n in children:
                        if n['kind']=='List':raise Unknown('nested List')
                        if n['kind']=='ForEach':callbacks.append(n)
                        find(n['children'])
                find(node['children'])
                good=[]
                for callback in callbacks:
                    def texts(children):
                        return [n['text'] for n in children if n.get('text')]+[t for n in children for t in texts(n['children'])]
                    bound=texts(callback['children'])
                    if bound and all(r['inside_list_item'] for r in bound):good.append(dict(callback,reads=bound))
                sites.append(dict(start_line=node['start_line'],end_line=node['end_line'],
                    start_offset=node['start_offset'],end_offset=node['end_offset'],axis=node['axis'],axis_range=node.get('axis_range'),
                    positive=node['axis']=='Vertical' and len(callbacks)==1 and len(good)==1,bindings=good))
            else:sites.extend(self.list_sites(node['children']))
            if node['kind']=='Scroll':raise Unknown('Scroll layout ambiguity')
        return sites

def parse_vertical_list_file(source,wanted_owners):
    try:
        if type(source)is not str or len(source.encode('utf-8'))>2*1024*1024:return None
        if isinstance(wanted_owners,(str,bytes)):return None
        wanted=set(wanted_owners)
        if any(type(n)is not str or not NAME.fullmatch(n) or n in RESERVED|API for n in wanted):return None
        return Parser(source).parse(wanted)
    except (Unknown,ValueError,TypeError,IndexError,KeyError,UnicodeError,RecursionError):return None
