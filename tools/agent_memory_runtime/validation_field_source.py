# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Closed local validation-source grammar, not runtime flow or serving authority."""
import re
from .ui_divider_source import Unknown, RESERVED
from .validation_field_lexical import tokenize_validation, template

FORBIDDEN = {'promptAction', 'trim', 'length', 'console', 'Promise'}

def parts(name):
    return tuple(x.lower() for x in re.findall(r'[A-Z]+(?=[A-Z][a-z]|$)|[A-Z]?[a-z]+|[0-9]+', name.replace('_', ' ').replace('$', ' ')))

class Parser:
    def __init__(self, source):
        self.t, self.pairs = tokenize_validation(source)
        self.i = 0
        self.decls = {}
        self.imports = set()

    def at(self, value):
        return self.i < len(self.t) and self.t[self.i].value == value and self.t[self.i].kind not in {'string', 'template'}

    def eat(self, value):
        if not self.at(value): raise Unknown('expected ' + value)
        token = self.t[self.i]; self.i += 1
        return token

    def opt(self, value):
        if self.at(value): self.i += 1; return True
        return False

    def name(self):
        if self.i >= len(self.t): raise Unknown('missing identifier')
        token = self.t[self.i]
        if token.kind != 'name' or token.value in RESERVED | FORBIDDEN: raise Unknown('identifier/shadow')
        self.i += 1
        return token.value

    def end_statement(self):
        # Body slices end immediately before their closing brace.
        if self.opt(';'): return
        if self.i == len(self.t) or self.at('}'): return
        if self.i and self.t[self.i].line > self.t[self.i - 1].line: return
        raise Unknown('missing statement separator')

    def primitive(self):
        if self.i >= len(self.t): raise Unknown('literal')
        t = self.t[self.i]
        if t.kind == 'template': raise Unknown('template primitive position')
        if t.kind not in {'string','number'} and t.value not in {'true','false','null'}: raise Unknown('literal')
        self.i += 1

    def parse(self):
        while self.i < len(self.t):
            if self.opt('import'):
                self.eat('{'); names = [self.name()]
                while self.opt(','): names.append(self.name())
                self.eat('}'); self.eat('from')
                if self.i >= len(self.t) or self.t[self.i].kind != 'string': raise Unknown('import path')
                self.i += 1; self.end_statement()
                for n in names:
                    if n in self.imports or n in self.decls: raise Unknown('duplicate import')
                    self.imports.add(n)
                continue
            decorators = []
            while self.opt('@'): decorators.append(self.name())
            if len(decorators) != len(set(decorators)) or any(n not in {'Component','Entry'} for n in decorators): raise Unknown('decorator')
            self.opt('export')
            start = self.i
            if self.i >= len(self.t) or self.t[self.i].kind == 'template' or self.t[self.i].value not in {'interface','class','struct'}: raise Unknown('declaration')
            kind = self.t[self.i].value; self.i += 1; owner = self.name()
            if owner in self.decls or owner in self.imports: raise Unknown('duplicate declaration')
            if decorators and kind != 'struct': raise Unknown('component kind')
            self.eat('{'); fields = {}; methods = {}
            while not self.at('}'):
                member_start = self.i
                state = self.opt('@')
                if state: self.eat('State')
                modifier = None
                if self.at('private') or self.at('public') or self.at('protected'):
                    modifier = self.t[self.i].value; self.i += 1
                async_ = self.opt('async')
                # 'build' remains globally reserved. Only the exact empty member
                # shape below may consume it; no ordinary identifier relaxation.
                contextual_build = self.at('build')
                if contextual_build:
                    self.eat('build'); member = 'build'
                else:
                    member = self.name()
                if member in fields or member in methods: raise Unknown('duplicate member')
                if contextual_build and (kind == 'interface' or state or modifier or async_):
                    raise Unknown('empty auxiliary modifiers')
                if contextual_build and not self.at('('):
                    raise Unknown('reserved build member')
                if self.opt(':'):
                    if async_ or (kind == 'interface' and (state or modifier)): raise Unknown('field modifiers')
                    typ = 'string' if self.opt('string') else self.name()
                    if kind != 'interface':
                        self.eat('=')
                        if typ == 'string':
                            if self.i >= len(self.t) or self.t[self.i].kind != 'string': raise Unknown('string init')
                            self.i += 1
                        else:
                            if state: raise Unknown('object State')
                            self.eat('new'); self.eat(typ); self.eat('('); self.eat(')')
                    elif typ != 'string': raise Unknown('interface property')
                    fields[member] = typ; self.end_statement(); continue
                if kind == 'interface' or state: raise Unknown('unsupported member')
                self.eat('('); params = {}
                while not self.at(')'):
                    n = self.name(); self.eat(':'); typ = 'string' if self.opt('string') else self.name()
                    if n in params or n in fields: raise Unknown('parameter shadow')
                    params[n] = typ
                    if not self.opt(','): break
                self.eat(')')
                if contextual_build or self.at('{'):
                    if params or state or modifier or async_:
                        raise Unknown('empty auxiliary signature')
                    opening = self.i; self.eat('{'); end = self.pairs[opening]
                    if end != self.i:
                        raise Unknown('nonempty untyped auxiliary')
                    self.i = end + 1
                    methods[member] = dict(name=member, params={}, async_=False,
                                           body=[], return_type=None, untyped_empty_aux=True,
                                           start=self.t[member_start].line, end=self.t[end].line)
                    continue
                self.eat(':')
                return_type = 'void'
                if self.opt('Promise'):
                    if not async_: raise Unknown('nonasync Promise')
                    self.eat('<'); self.eat('void'); self.eat('>')
                elif self.at('string') or self.at('number') or self.at('boolean'):
                    if async_: raise Unknown('async primitive auxiliary')
                    return_type = self.t[self.i].value; self.i += 1
                else: self.eat('void')
                opening = self.i; self.eat('{'); end = self.pairs[opening]
                body = self.t[self.i:end]; self.i = end + 1
                methods[member] = dict(name=member, params=params, async_=async_, body=body, return_type=return_type,
                                       start=self.t[member_start].line, end=self.t[end].line)
            end = self.eat('}')
            self.decls[owner] = dict(owner=owner, kind=kind, start=self.t[start].line,
                                     end=end.line, fields=fields, methods=methods)
        result = []
        for d in self.decls.values():
            for typ in d['fields'].values():
                if typ != 'string' and typ not in self.decls and typ not in self.imports: raise Unknown('unknown field type')
            for m in d['methods'].values():
                if any(n in d['fields'] for n in m['params']): raise Unknown('parameter shadow')
                for typ in m['params'].values():
                    if typ != 'string' and (typ not in self.decls or self.decls[typ]['kind'] != 'interface'): raise Unknown('parameter type')
                proof = self.body(d, m)
                if proof: result.append(proof)
        return result

    def body(self, d, m):
        if m.get('untyped_empty_aux'):
            return None
        saved = self.t, self.i
        self.t, self.i = m['body'], 0
        try:
            if m['return_type'] != 'void':
                start = self.eat('return')
                if self.i >= len(self.t): raise Unknown('missing auxiliary return value')
                literal = self.t[self.i]
                expected = m['return_type']
                matched = ((expected == 'string' and literal.kind == 'string')
                           or (expected == 'number' and literal.kind == 'number')
                           or (expected == 'boolean' and literal.kind == 'name' and literal.value in {'true','false'}))
                if not matched or literal.line != start.line: raise Unknown('typed auxiliary literal/ASI')
                self.i += 1; self.end_statement()
                if self.i != len(self.t): raise Unknown('auxiliary return tail')
                return None
            if not self.t: return None
            if self.at('return'): raise Unknown('void auxiliary value return')
            if not self.opt('if'):
                count = 0
                while self.i < len(self.t):
                    self.call(d,m,None); count += 1
                    if count > 2: raise Unknown('auxiliary calls')
                return None
            self.eat('(')
            root = 'this' if self.opt('this') else self.name()
            self.eat('.'); field = self.name()
            if root == 'this':
                if d['fields'].get(field) != 'string': raise Unknown('own member')
            else:
                typ = m['params'].get(root); interface = self.decls.get(typ, {})
                if interface.get('kind') != 'interface' or interface['fields'].get(field) != 'string': raise Unknown('parameter member')
            for token in ('.','trim','(',')','.','length'): self.eat(token)
            eq = [self.eat('=') for _ in range(3)]
            if eq[0].end != eq[1].start or eq[1].end != eq[2].start: raise Unknown('split equality')
            for token in ('0',')','{','promptAction','.','showToast','(','{','message',':'): self.eat(token)
            if self.i >= len(self.t) or self.t[self.i].kind != 'string': raise Unknown('toast string')
            self.i += 1
            for token in ('}',')'): self.eat(token)
            self.end_statement(); self.eat('return'); self.end_statement(); self.eat('}')
            target,arg = self.call(d,m,(root,field))
            if 'dispatch' not in parts(target): raise Unknown('dispatch identifier part')
            extra = 0
            while self.i < len(self.t):
                self.call(d,m,(root,field)); extra += 1
                if extra > 2: raise Unknown('tail call cap')
            return dict(owner=d['owner'],owner_start=d['start'],owner_end=d['end'],kind=d['kind'],
                        method=m['name'],start_line=m['start'],end_line=m['end'],field=field,root=root,dispatch_argument=arg)
        finally: self.t,self.i = saved

    def call(self,d,m,bound):
        call_line = self.t[self.i].line if self.i < len(self.t) else None
        if self.opt('await') and not m['async_']: raise Unknown('await')
        if self.opt('this'):
            self.eat('.'); first=self.name()
            if self.opt('.'):
                target=self.name(); typ=d['fields'].get(first)
                if not typ or typ=='string': raise Unknown('receiver field')
                local=self.decls.get(typ)
                if local is not None and target not in local['methods']: raise Unknown('receiver method')
                if local is not None and local['methods'][target].get('untyped_empty_aux'):
                    raise Unknown('untyped auxiliary receiver target')
                if local is None and typ not in self.imports: raise Unknown('receiver type')
            else:
                target=first
                if target not in d['methods']: raise Unknown('direct method')
                if d['methods'][target].get('untyped_empty_aux'):
                    raise Unknown('untyped auxiliary direct target')
        elif bound is None and self.opt('console'):
            self.eat('.')
            if not any(self.opt(x) for x in ('info','warn','error','log','debug')): raise Unknown('console call')
            target='console'
        else: raise Unknown('call receiver')
        self.eat('('); arg=None; count=0
        if self.i < len(self.t) and self.t[self.i].kind == 'template':
            token = self.t[self.i]
            if bound is not None or target != 'console': raise Unknown('template call position')
            _, parameter = template(token.value, 0)
            if parameter in RESERVED | FORBIDDEN or m['params'].get(parameter) != 'string':
                raise Unknown('template string parameter')
            self.i += 1
            closing = self.eat(')')  # Sole argument; comma/second argument is rejected.
            if closing.line != call_line or token.line != call_line:
                raise Unknown('multiline template console call')
            self.end_statement()
            return target, arg
        while not self.at(')'):
            count+=1
            if bound:
                root,field=bound; self.eat(root)
                if self.opt('.'): self.eat(field); arg='scalar'
                elif root!='this': arg='containing_object'
                else: raise Unknown('this object argument')
                if count!=1: raise Unknown('argument arity')
            elif self.opt('this'):
                self.eat('.'); name=self.name()
                if name not in d['fields']: raise Unknown('argument own field')
            elif self.i<len(self.t) and self.t[self.i].kind=='name' and self.t[self.i].value in m['params']:
                self.i+=1
            else: self.primitive()
            if not self.opt(','): break
        self.eat(')'); self.end_statement()
        if bound and count!=1: raise Unknown('missing argument')
        return target,arg

def parse_validation_field_file(source):
    try:
        if type(source) is not str or len(source.encode('utf-8')) > 2*1024*1024: return None
        return Parser(source).parse()
    except (Unknown, IndexError, KeyError, UnicodeError, RecursionError): return None
