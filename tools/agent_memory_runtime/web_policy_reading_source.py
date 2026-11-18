"""Closed ArkUI Web-chain reading evidence, not execution/security verification."""
from .validation_field_lexical import tokenize_validation
from .ui_divider_source import Unknown


class Parser:
    def __init__(self, source):
        self.t, self.pairs = tokenize_validation(source)
        self.i = 0
        self.namespace = None
        self.methods = []

    def at(self, value):
        return self.i < len(self.t) and self.t[self.i].kind != 'string' and self.t[self.i].value == value

    def eat(self, value):
        if not self.at(value): raise Unknown(value)
        t = self.t[self.i]; self.i += 1
        return t

    def opt(self, value):
        if self.at(value): self.i += 1; return True
        return False

    def name(self):
        if self.i >= len(self.t) or self.t[self.i].kind != 'name': raise Unknown('name')
        value = self.t[self.i].value; self.i += 1
        if value == self.namespace or value in {'Web', 'Column', 'Text', 'build', 'this', 'return'}: raise Unknown('shadow')
        return value

    def string(self):
        if self.i >= len(self.t) or self.t[self.i].kind != 'string': raise Unknown('string')
        value = self.t[self.i].value; self.i += 1
        return value

    def parse(self):
        if self.opt('import'):
            self.namespace = self.name(); self.eat('from')
            if self.string() != '@ohos.web.webview': raise Unknown('SDK')
            self.opt(';')
        facts = []; owners = set()
        while self.i < len(self.t):
            self.eat('@'); self.eat('Component'); self.opt('export')
            start = self.eat('struct').line; owner = self.name()
            if owner in owners: raise Unknown('duplicate')
            owners.add(owner); self.eat('{'); fields = {}; built = False
            while not self.at('}'):
                if self.opt('private'):
                    name = self.name(); self.eat(':')
                    if not self.namespace: raise Unknown('controller')
                    self.eat(self.namespace); self.eat('.'); self.eat('WebviewController'); self.eat('='); self.eat('new')
                    self.eat(self.namespace); self.eat('.'); self.eat('WebviewController'); self.eat('('); self.eat(')'); kind = 'controller'
                elif self.opt('@'):
                    self.eat('Prop'); name = self.name(); self.eat(':'); self.eat('string'); self.eat('='); self.string(); kind = 'src'
                elif self.at('build'):
                    if built: raise Unknown('duplicate build')
                    built = True; lo = self.eat('build').line; self.eat('('); self.eat(')'); self.eat('{')
                    self.eat('Column'); self.eat('('); self.eat(')'); self.eat('{')
                    chains = []
                    while not self.at('}'):
                        if self.opt('Text'):
                            self.eat('('); self.string(); self.eat(')'); self.opt(';'); continue
                        chains.append(self.chain(fields)); self.opt(';')
                    self.eat('}'); hi = self.eat('}').line
                    self.methods.append(dict(owner=owner,method='build',start_line=lo,end_line=hi,class_start=start))
                    for chain in chains:
                        if chain: facts.append(dict(owner=owner,method='build',start_line=lo,end_line=hi,class_start=start))
                    continue
                else: raise Unknown('member')
                if name in fields: raise Unknown('duplicate field')
                fields[name] = kind; self.opt(';')
            end = self.eat('}').line
            for f in [*facts,*self.methods]:
                if f['owner'] == owner: f['class_end'] = end
            if not built: raise Unknown('no build')
        return facts

    def chain(self, fields):
        self.eat('Web'); self.eat('('); self.eat('{')
        args = {}
        while not self.at('}'):
            key = self.name(); self.eat(':'); self.eat('this'); self.eat('.'); field = self.name()
            if key in args: raise Unknown('duplicate argument')
            args[key] = fields.get(field)
            if not self.opt(','): break
        self.eat('}'); self.eat(')')
        if args != {'src':'src','controller':'controller'}: raise Unknown('Web arguments')
        seen = set()
        while self.opt('.'):
            op = self.name()
            if op in seen: raise Unknown('duplicate modifier')
            seen.add(op); self.eat('(')
            if op == 'fileAccess':
                if not (self.opt('true') or self.opt('false')): raise Unknown('access value')
            elif op == 'onLoadIntercept':
                self.eat('('); self.name(); self.eat(')'); self.eat('=>')
                opening = self.i; self.eat('{'); closing = self.pairs.get(opening)
                if closing is None: raise Unknown('callback')
                # Callback internals are not interpreted. Nested Web/shadowing can
                # hide a second chain, so decline rather than certify absence.
                if any(t.kind == 'name' and t.value in {'Web','eval','Function'} for t in self.t[self.i:closing]):
                    raise Unknown('nested or dynamic Web')
                self.i = closing + 1
            else: raise Unknown('modifier')
            self.eat(')')
        return seen == {'fileAccess','onLoadIntercept'}


def web_policy_chains(source):
    try:
        return Parser(source).parse()
    except (Unknown, IndexError, KeyError, RecursionError):
        return None


def web_policy_inventory(source):
    try:
        parser = Parser(source)
        facts = parser.parse()
        return {'chains': facts, 'methods': parser.methods}
    except (Unknown, IndexError, KeyError, RecursionError):
        return None
