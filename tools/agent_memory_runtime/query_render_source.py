# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Closed source syntax witness, not execution, type or cleanup-safety proof."""
from dataclasses import dataclass
import re

PROTECTED = {'Text', 'Column', 'Row', 'RegExp'}
RESERVED = set('if else for while do switch case default try catch finally with function class return throw new delete void typeof instanceof in of yield await import export const let var break continue debugger super this async get set constructor true false null undefined struct extends'.split())
IDENT = re.compile(r'[A-Za-z_$][A-Za-z0-9_$]*')
NUMBER = re.compile(r'[0-9]+(?:\.[0-9]+)?')
TAG = re.compile(r'<(?:[A-Za-z][A-Za-z0-9]*|/[A-Za-z][A-Za-z0-9]*|[A-Za-z][A-Za-z0-9]* /)>')


class Unknown(ValueError):
    pass


@dataclass(frozen=True)
class Token:
    value: str
    kind: str
    start: int
    end: int
    line: int


def lex(source, *, allow_arrow=False):
    tokens = []
    pos = 0
    line = 1
    while pos < len(source):
        char = source[pos]
        if char in ' \t\r\n':
            line += char == '\n'
            pos += 1
            continue
        if source.startswith('//', pos):
            end = source.find('\n', pos + 2)
            pos = len(source) if end < 0 else end
            continue
        if source.startswith('/*', pos):
            end = source.find('*/', pos + 2)
            if end < 0:
                raise Unknown()
            line += source.count('\n', pos, end + 2)
            pos = end + 2
            continue
        start = pos
        first_line = line
        if char in "'\"":
            quote = char
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
            value = ''.join(parts)
            kind = 'string'
        else:
            match = IDENT.match(source, pos)
            number = NUMBER.match(source, pos)
            if match:
                value = match.group(); pos = match.end(); kind = 'ident'
            elif number:
                value = number.group(); pos = number.end(); kind = 'number'
            elif allow_arrow and source.startswith('=>', pos):
                value = '=>'; pos += 2; kind = 'punct'
            elif char in '@{}().,:;=-':
                value = char; pos += 1; kind = 'punct'
            else:
                # Includes regex literals, templates, unknown operators and delimiters.
                raise Unknown()
        tokens.append(Token(value, kind, start, pos, first_line))
    tokens.append(Token('', 'eof', len(source), len(source), line))
    return tokens


class Parser:
    def __init__(self, source):
        self.source = source
        self.tokens = lex(source)
        self.pos = 0
        self.names = set()
        self.methods = {}
        self.constructors = set()

    def peek(self, value):
        token = self.tokens[self.pos]
        return token.kind != 'string' and token.value == value

    def take(self, value=None, kind=None):
        token = self.tokens[self.pos]
        if ((value is not None and (token.value != value or token.kind == 'string'))
                or (kind is not None and token.kind != kind) or token.kind == 'eof'):
            raise Unknown()
        self.pos += 1
        return token

    def optional(self, value):
        if self.peek(value):
            self.take(value)
            return True
        return False

    def identifier(self):
        token = self.take(kind='ident')
        if token.value in RESERVED:
            raise Unknown()
        return token

    def declare(self, name):
        if name in self.names or name in PROTECTED:
            raise Unknown()
        self.names.add(name)

    def separator(self):
        if self.optional(';'):
            return
        previous = self.tokens[self.pos - 1]
        current = self.tokens[self.pos]
        if '\n' not in self.source[previous.end:current.start]:
            raise Unknown()

    def field_reference(self):
        self.take('this'); self.take('.')
        name = self.identifier().value
        if self.peek('.') and self.tokens[self.pos + 2].value != '(':
            self.take('.')
            self.identifier()
        return name

    def build(self):
        self.take('('); self.take(')')
        if self.optional(':'):
            self.take('void')
        self.take('{')
        container = self.take(kind='ident').value
        if container not in {'Column', 'Row'}:
            raise Unknown()
        self.take('('); self.take(')'); self.take('{')
        calls = []
        count = 0
        while not self.peek('}'):
            if count:
                self.separator()
            self.take('Text'); self.take('(')
            if self.tokens[self.pos].kind == 'string':
                self.take(kind='string')
            else:
                self.take('this'); self.take('.')
                name = self.identifier().value
                if self.optional('('):
                    self.take(')'); calls.append(name)
                elif self.optional('.'):
                    self.identifier()
            self.take(')')
            count += 1
            if count > 8:
                raise Unknown()
            # A terminal semicolon may precede the container close.
            if self.peek(';') and self.tokens[self.pos + 1].value == '}':
                self.take(';')
        self.take('}'); end = self.take('}')
        if count == 0 or len(calls) != 1:
            raise Unknown()
        return end, calls[0]

    def helper(self):
        self.take('('); self.take(')'); self.take(':'); self.take('string'); self.take('{')
        ret = self.take('return')
        if self.tokens[self.pos].line != ret.line:
            raise Unknown()
        self.field_reference()
        count = 0
        while self.optional('.'):
            self.take('replace'); self.take('(')
            if self.optional('new'):
                self.take('RegExp'); self.take('(')
                if self.take(kind='string').value not in {'<[^>]+>', '<[^>]*>'}:
                    raise Unknown()
                if self.optional(',') and self.take(kind='string').value not in {'', 'g'}:
                    raise Unknown()
                self.take(')'); self.take(',')
                if self.take(kind='string').value != '':
                    raise Unknown()
            else:
                if TAG.fullmatch(self.take(kind='string').value) is None:
                    raise Unknown()
                self.take(',')
                if self.take(kind='string').value not in {'', '\n'}:
                    raise Unknown()
            self.take(')')
            count += 1
            if count > 8:
                raise Unknown()
        self.optional(';')
        end = self.take('}')
        if not count:
            raise Unknown()
        return end

    def field(self):
        declared_type = None
        if self.optional(':'):
            declared_type = self.identifier().value
        self.take('=')
        if self.optional('new'):
            constructor = self.identifier().value
            if constructor in PROTECTED | {'build'} or constructor != declared_type:
                raise Unknown()
            self.constructors.add(constructor)
            self.take('('); self.take(')')
        elif self.tokens[self.pos].kind == 'string':
            self.take(kind='string')
        elif self.peek('true') or self.peek('false'):
            self.take()
        else:
            self.optional('-'); self.take(kind='number')
        if self.peek('}'):
            return
        self.separator()

    def parse(self):
        while self.optional('import'):
            self.take('{')
            self.declare(self.identifier().value)
            while self.optional(','):
                self.declare(self.identifier().value)
            self.take('}'); self.take('from')
            path = self.take(kind='string').value
            if not re.fullmatch(r'\.{1,2}/[A-Za-z0-9_./-]+', path):
                raise Unknown()
            self.separator()
        self.take('@')
        if self.take(kind='ident').value not in {'Component', 'ComponentV2'}:
            raise Unknown()
        self.take('export'); self.take('struct')
        owner = self.identifier().value
        self.declare(owner); self.take('{')
        helper_call = None
        while not self.peek('}'):
            decorated = False
            if self.optional('@'):
                decorated = True
                if self.take(kind='ident').value not in {'State', 'Prop', 'Param'}:
                    raise Unknown()
            visibility = self.optional('private') or self.optional('public')
            token = self.identifier()
            name = token.value
            self.declare(name)
            if self.peek('('):
                if decorated or visibility:
                    raise Unknown()
                if name == 'build':
                    end, helper_call = self.build()
                else:
                    end = self.helper()
                if end.end - token.start > 32768:
                    raise Unknown()
                self.methods[name] = (token.line, end.line)
            else:
                self.field()
        self.take('}')
        if self.tokens[self.pos].kind != 'eof':
            raise Unknown()
        if (helper_call in self.constructors or helper_call in PROTECTED | RESERVED | {'build'} or
                set(self.methods) != {'build', helper_call}):
            raise Unknown()
        return {'owner': owner, 'build_start': self.methods['build'][0],
                'build_end': self.methods['build'][1], 'helper': helper_call,
                'helper_start': self.methods[helper_call][0],
                'helper_end': self.methods[helper_call][1]}


def parse_render_source(source):
    """Return exact 1-based method ranges for the closed syntax, else unknown."""
    if not isinstance(source, str) or '\u2028' in source or '\u2029' in source:
        return None
    try:
        if len(source.encode('utf-8')) > 2 * 1024 * 1024:
            return None
    except UnicodeEncodeError:
        return None
    source = source.replace('\r\n', '\n').replace('\r', '\n')
    try:
        return Parser(source).parse()
    except (Unknown, IndexError):
        return None
