# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Closed recovery role source shapes; offsets are original string characters."""
import re
from .query_render_source import Token, Unknown, IDENT, Parser as TokenParser
from .text import identifier_tokens

KEYWORDS = set('this super new return if else await async class constructor const let var void boolean string number null true false function extends implements get set static private public protected export import default from as try catch finally throw for while do switch case break continue yield interface type'.split())


def lex(source):
    # Same finite quote/comment strategy as query_render_source, with the fixed
    # array and Promise punctuation needed by this separate grammar.
    result = []
    pos = 0
    line = 1
    while pos < len(source):
        c = source[pos]
        if c in ' \t\r\n':
            if c == '\n' or (c == '\r' and not source.startswith('\r\n', pos)):
                line += 1
            pos += 1
            continue
        if source.startswith('//', pos):
            while pos < len(source) and source[pos] not in '\r\n':
                pos += 1
            continue
        if source.startswith('/*', pos):
            end = source.find('*/', pos + 2)
            if end < 0:
                raise Unknown()
            line += len(re.findall(r'\r\n|\r|\n', source[pos:end + 2]))
            pos = end + 2
            continue
        start = pos
        if c in "'\"":
            quote = c
            parts = []
            pos += 1
            while pos < len(source) and source[pos] != quote:
                c = source[pos]
                if c in '\r\n':
                    raise Unknown()
                if c == '\\':
                    pos += 1
                    if pos >= len(source) or source[pos] not in "'\"\\n":
                        raise Unknown()
                    c = '\n' if source[pos] == 'n' else source[pos]
                parts.append(c)
                pos += 1
            if pos >= len(source):
                raise Unknown()
            pos += 1
            value, kind = ''.join(parts), 'string'
        else:
            match = IDENT.match(source, pos)
            if match:
                value, kind = match.group(), 'ident'
                pos = match.end()
            elif c in '@{}().,:;=[]<>':
                value, kind = c, 'punct'
                pos += 1
            else:
                raise Unknown()
        result.append(Token(value, kind, start, pos, line))
    result.append(Token('', 'eof', len(source), len(source), line))
    return result


def components(name):
    return set(identifier_tokens(name)) | {name.casefold()}


def span(start, end):
    return {'start_line': start.line, 'end_line': end.line,
            'start_offset': start.start, 'end_offset': end.end}


class RecoveryParser(TokenParser):
    def __init__(self, source):
        self.source = source
        self.tokens = lex(source)
        self.pos = 0
        self.names = set()
        self.fields = []
        self.methods = []
        self.imports = set()

    def identifier(self):
        token = self.take(kind='ident')
        if token.value in KEYWORDS:
            raise Unknown()
        return token

    def declare(self, name):
        if name in self.names:
            raise Unknown()
        self.names.add(name)

    def statement_end(self, closing_allowed=True):
        if self.optional(';'):
            return
        if closing_allowed and self.peek('}'):
            return
        previous, current = self.tokens[self.pos - 1], self.tokens[self.pos]
        if not any(c in self.source[previous.end:current.start] for c in '\r\n'):
            raise Unknown()

    def new_constructor(self):
        self.take('new')
        name = self.identifier().value
        self.take('('); self.take(')')
        return name

    def plain_field(self):
        first = self.take('private')
        name = self.identifier().value
        self.declare(name)
        self.take(':'); type_name = self.identifier().value
        ctor = self.new_constructor() if self.optional('=') else None
        self.statement_end()
        self.fields.append(dict(name=name, type=type_name, kind='plain',
                                constructor=ctor, **span(first, self.tokens[self.pos - 1])))

    def state_field(self):
        first = self.take('@'); self.take('State')
        name = self.identifier().value
        self.declare(name)
        self.take(':'); type_name = self.identifier().value
        self.take('['); self.take(']'); self.take('='); self.take('['); self.take(']')
        self.statement_end()
        self.fields.append(dict(name=name, type=type_name, kind='state',
                                constructor=None, **span(first, self.tokens[self.pos - 1])))

    def branch(self):
        self.take('{'); self.take('this'); self.take('.')
        field = self.identifier().value
        self.take('='); constructor = self.new_constructor()
        self.statement_end(); self.take('}')
        return field, constructor

    def selection(self):
        first = self.identifier()
        name = first.value
        self.declare(name)
        self.take('('); flag = self.identifier().value
        self.take(':'); self.take('boolean'); self.take(')')
        self.take(':'); self.take('void'); self.take('{')
        self.take('if'); self.take('('); self.take(flag); self.take(')')
        left_field, left = self.branch()
        self.take('else'); right_field, right = self.branch()
        end = self.take('}')
        if left_field != right_field or left == right:
            raise Unknown()
        self.methods.append(dict(name=name, kind='registry', field=left_field,
                                 parameter=flag, left=left, right=right, **span(first, end)))

    def synchronization(self):
        first = self.take('async')
        name_token = self.identifier()
        name = name_token.value
        if name_token.line != first.line:
            raise Unknown()
        self.declare(name)
        self.take('('); self.take(')'); self.take(':'); self.take('Promise')
        self.take('<'); self.take('void'); self.take('>'); self.take('{')
        self.take('const'); local = self.identifier().value
        self.take('='); self.take('await'); self.take('this'); self.take('.')
        field = self.identifier().value
        self.take('.'); read = self.identifier().value
        self.take('('); self.take(')')
        self.statement_end(closing_allowed=False)
        self.take('this'); self.take('.')
        state = self.identifier().value
        self.take('='); self.take(local)
        self.statement_end(); end = self.take('}')
        if 'sync' not in components(name):
            raise Unknown()
        self.methods.append(dict(name=name, kind='store', field=field, state=state,
                                 local=local, read=read, **span(first, end)))

    def parse(self):
        while self.optional('import'):
            self.take('{')
            name = self.identifier().value
            self.declare(name); self.imports.add(name)
            while self.optional(','):
                name = self.identifier().value
                self.declare(name); self.imports.add(name)
            self.take('}'); self.take('from')
            path = self.take(kind='string').value
            if not re.fullmatch(r'\.{1,2}/[A-Za-z0-9_./-]+', path):
                raise Unknown()
            self.statement_end(closing_allowed=False)
        first = self.tokens[self.pos]
        self.optional('export'); self.take('class')
        owner = self.identifier().value
        self.declare(owner); self.take('{')
        while not self.peek('}'):
            if self.peek('private'):
                self.plain_field()
            elif self.peek('@'):
                self.state_field()
            elif self.peek('async'):
                self.synchronization()
            else:
                self.selection()
            if len(self.fields) > 4 or len(self.methods) > 2:
                raise Unknown()
        end = self.take('}')
        if self.tokens[self.pos].kind != 'eof' or not self.methods:
            raise Unknown()
        fields = {f['name']: f for f in self.fields}
        methods = {m['name'] for m in self.methods}
        bindings = set(fields)
        constructors = {f['constructor'] for f in self.fields if f['constructor']}
        roles = []
        for method in self.methods:
            if method['end_offset'] - method['start_offset'] > 32768:
                raise Unknown()
            field = fields.get(method['field'])
            if field is None or field['kind'] != 'plain':
                raise Unknown()
            binding = method.get('parameter', method.get('local'))
            if binding in bindings or binding in methods or binding in self.imports or binding == owner:
                raise Unknown()
            bindings.add(binding)
            if method['kind'] == 'registry':
                constructors.update((method['left'], method['right']))
                if 'registry' in components(owner):
                    roles.append('registry')
            else:
                state = fields.get(method['state'])
                if state is None or state['kind'] != 'state':
                    raise Unknown()
                if 'store' in components(owner):
                    roles.append('store')
        if constructors & methods:
            raise Unknown()
        if not roles:
            raise Unknown()
        return dict(owner=owner, class_start=first.line, class_end=end.line,
                    class_start_offset=first.start, class_end_offset=end.end,
                    fields=self.fields, methods=self.methods, roles=sorted(set(roles)))


def parse_recovery_source(source):
    if not isinstance(source, str) or '\u2028' in source or '\u2029' in source:
        return None
    try:
        if len(source.encode('utf-8')) > 2 * 1024 * 1024:
            return None
        return RecoveryParser(source).parse()
    except (Unknown, IndexError, UnicodeError):
        return None
