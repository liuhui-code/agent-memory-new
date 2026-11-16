# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Closed gesture registration syntax, not SDK resolution or runtime effects."""
from .ui_divider_source import NAME, RESERVED, Unknown, tokenize

SHADOW = {'Stack', 'PanGesture', 'gesture', 'onActionUpdate'}
SCALARS = {'number', 'string', 'boolean'}


class ParsedGesture(dict):
    """Source inventory only; this object grants no serving authority."""
    def __init__(self, frames, declarations):
        super().__init__(frames)
        self.declarations = tuple(declarations)
        self.declared_names = tuple(d['name'] for d in declarations)


def potential(token):
    return token.kind == 'name' and (token.value in SHADOW - {'Stack'}
                                    or token.value.endswith('Gesture')
                                    or token.value.startswith('onAction'))


class Parser:
    def __init__(self, source, tokens, pairs, start=0, stop=None):
        self.source = source
        self.t = tokens
        self.pairs = pairs
        self.i = start
        self.stop = len(tokens) if stop is None else stop

    def at(self, value):
        return (self.i < self.stop and self.t[self.i].kind != 'string'
                and self.t[self.i].value == value)

    def eat(self, value):
        if not self.at(value):
            raise Unknown('expected ' + value)
        token = self.t[self.i]
        self.i += 1
        return token

    def maybe(self, value):
        if self.at(value):
            self.i += 1
            return True
        return False

    def ident(self, binding=False):
        if self.i >= self.stop or self.t[self.i].kind != 'name':
            raise Unknown('identifier')
        token = self.t[self.i]
        self.i += 1
        if token.value in RESERVED or (binding and token.value in SHADOW):
            raise Unknown('reserved or shadow identifier')
        return token

    def end(self, previous):
        if self.maybe(';'):
            return
        following = self.t[self.i] if self.i < len(self.t) else None
        if following and (following.kind == 'punct' and following.value == '}'
                          or following.line > previous.line):
            return
        raise Unknown('missing statement or member separator')

    def scalar_type(self):
        if self.i >= self.stop or self.t[self.i].kind != 'name' or self.t[self.i].value not in SCALARS:
            raise Unknown('scalar type')
        value = self.t[self.i].value
        self.i += 1
        return value

    def scalar(self, type_name):
        if self.i >= self.stop:
            raise Unknown('scalar value')
        token = self.t[self.i]
        valid = ((type_name == 'number' and token.kind == 'number')
                 or (type_name == 'string' and token.kind == 'string')
                 or (type_name == 'boolean' and token.kind == 'name' and token.value in ('true', 'false')))
        if not valid:
            raise Unknown('literal kind differs from field type')
        self.i += 1
        return token

    def visibility(self):
        if self.at('private') or self.at('public'):
            self.i += 1

    def state(self):
        first = self.eat('@')
        self.eat('State')
        self.visibility()
        name = self.ident(binding=True).value
        self.eat(':')
        scalar_type = self.scalar_type()
        self.eat('=')
        last = self.scalar(scalar_type)
        self.end(last)
        return name, dict(kind='state', type_name=scalar_type, start_line=first.line, end_line=last.line)

    def instance(self):
        first = self.t[self.i]
        self.visibility()
        name = self.ident(binding=True).value
        self.eat(':')
        type_name = self.ident(binding=True).value
        self.eat('=')
        self.eat('new')
        if self.ident(binding=True).value != type_name:
            raise Unknown('constructor type spelling mismatch')
        self.eat('(')
        last = self.eat(')')
        self.end(last)
        return name, dict(kind='instance', type_name=type_name, start_line=first.line, end_line=last.line)

    def argument(self, param):
        first = self.ident()
        if first.value != param:
            raise Unknown('argument is not this callback parameter')
        self.eat('.')
        member = self.ident()
        return dict(param=param, member=member.value, start_line=first.line, end_line=member.line)

    def statement(self, param):
        self.eat('this')
        self.eat('.')
        field = self.ident().value
        if self.maybe('='):
            arg = self.argument(param)
            return dict(action_kind='assignment', param=param, target=field,
                        member=arg['member'], method=None, args=[arg])
        self.eat('.')
        method = self.ident().value
        self.eat('(')
        args = [self.argument(param)]
        while self.maybe(','):
            if len(args) >= 3:
                raise Unknown('too many forwarding arguments')
            args.append(self.argument(param))
        self.eat(')')
        return dict(action_kind='forwarding', param=param, target=field,
                    member=None, method=method, args=args)

    def registration(self):
        stack = self.eat('Stack')
        self.eat('(')
        self.eat(')')
        self.eat('{')
        self.eat('}')
        self.eat('.')
        self.eat('gesture')
        self.eat('(')
        self.eat('PanGesture')
        self.eat('(')
        self.eat(')')
        dot = self.eat('.')
        registration = self.eat('onActionUpdate')
        # The existing producer indexes .onActionUpdate on its own physical line.
        if dot.line != registration.line:
            raise Unknown('unindexable split member name')
        self.eat('(')
        self.eat('(')
        parameter = self.ident(binding=True)
        if self.maybe(':'):
            self.eat('GestureEvent')
        self.eat(')')
        self.eat('=>')
        opening = self.eat('{')
        site = self.statement(parameter.value)
        self.maybe(';')
        closing = self.eat('}')
        self.eat(')')
        last = self.eat(')')
        self.end(last)
        site.update(callback_start=registration.line, callback_end=closing.line,
                    callback_start_line=registration.line, callback_end_line=closing.line,
                    callback_start_offset=registration.start, callback_end_offset=closing.end,
                    callback_start_byte=len(self.source[:registration.start].encode('utf-8')),
                    callback_end_byte=len(self.source[:closing.end].encode('utf-8')),
                    parameter_start=parameter.start, parameter_end=parameter.end,
                    body_start=opening.start, body_end=closing.end,
                    registration_start=stack.start, registration_end=last.end)
        return site

    def build(self):
        first = self.eat('build')
        self.eat('(')
        self.eat(')')
        opening = self.i
        self.eat('{')
        closing = self.pairs[opening]
        body = self.t[self.i:closing]
        # This first BODY grammar admits no bracket expression. Interface [] is
        # checked separately, never turned into computed member syntax.
        if any(t.kind == 'punct' and t.value in ('[', ']') for t in body):
            raise Unknown('computed/index/array expression in build')
        # A locally bound Stack cannot hide in the otherwise-negative body.
        for index in range(self.i, closing):
            token = self.t[index]
            if token.kind == 'name' and token.value == 'Stack':
                before = self.t[index - 1].value if index else ''
                if (index + 1 >= closing or self.t[index + 1].kind != 'punct'
                        or self.t[index + 1].value != '(' or before in ('function', 'class', 'struct')):
                    raise Unknown('Stack shadow or unresolved reference')
        sites = []
        if any(potential(t) for t in body):
            body_parser = Parser(self.source, self.t, self.pairs, self.i, closing)
            while body_parser.i < closing:
                sites.append(body_parser.registration())
            if not sites:
                raise Unknown('potential without complete registration')
            lines = [s['callback_start'] for s in sites]
            if len(set(lines)) != len(lines):
                raise Unknown('same-line callback identity ambiguity')
        self.i = closing + 1
        return first.line, self.t[closing].line, sites

    def component(self):
        self.eat('@')
        if self.maybe('Entry'):
            self.eat('@')
        self.eat('Component')
        self.maybe('export')
        first = self.eat('struct')
        name = self.ident(binding=True).value
        self.eat('{')
        fields = {}
        build = None
        while not self.at('}'):
            if self.i >= self.stop:
                raise Unknown('unclosed component')
            if self.at('build'):
                if build is not None:
                    raise Unknown('duplicate build')
                build = self.build()
            else:
                field, definition = self.state() if self.at('@') else self.instance()
                if field in fields:
                    raise Unknown('duplicate owner field')
                fields[field] = definition
        last = self.eat('}')
        if build is None:
            raise Unknown('missing build')
        start, end, sites = build
        for site in sites:
            field = fields.get(site['target'])
            expected = 'state' if site['action_kind'] == 'assignment' else 'instance'
            if field is None or field['kind'] != expected:
                raise Unknown('callback target is not the declared owner field')
            site['target_definition'] = dict(field)
        frame = dict(kind='component', owner_start=first.line, owner_end=last.line,
                     build_start=start, build_end=end, positive=bool(sites), sites=sites)
        return name, frame

    def interface(self):
        self.maybe('export')
        first = self.eat('interface')
        name = self.ident(binding=True).value
        self.eat('{')
        fields = set()
        while not self.at('}'):
            key = self.ident(binding=True).value
            if key in fields:
                raise Unknown('duplicate interface property')
            fields.add(key)
            self.eat(':')
            self.scalar_type()
            previous = self.t[self.i - 1]
            if self.maybe('['):
                previous = self.eat(']')
            self.end(previous)
        last = self.eat('}')
        return name, dict(kind='interface', owner_start=first.line, owner_end=last.line,
                          build_start=None, build_end=None, positive=False, sites=[])


def parse_gesture_file(source, wanted_names):
    """Closed source facts for requested declarations; None means unknown."""
    try:
        if not isinstance(source, str) or not source or isinstance(wanted_names, (str, bytes)):
            return None
        wanted = set(wanted_names)
        if not wanted or any(not isinstance(n, str) or not NAME.fullmatch(n) for n in wanted):
            return None
        tokens, pairs = tokenize(source)
        parser = Parser(source, tokens, pairs)
        frames, declarations = {}, []
        seen = set()
        while parser.i < parser.stop:
            if parser.at('@'):
                name, frame = parser.component()
            else:
                # All imports/classes/functions/aliases/unknown prefixes reject;
                # no component-only scan can skip a custom competing declaration.
                name, frame = parser.interface()
            if name in seen:
                raise Unknown('duplicate source declaration')
            seen.add(name)
            declarations.append(dict(name=name, kind=frame['kind'],
                                     start_line=frame['owner_start'], end_line=frame['owner_end']))
            if name in wanted:
                frames[name] = frame
        if set(frames) != wanted:
            return None
        return ParsedGesture(frames, declarations)
    except (Unknown, TypeError, ValueError, OverflowError, RecursionError, UnicodeError):
        return None
