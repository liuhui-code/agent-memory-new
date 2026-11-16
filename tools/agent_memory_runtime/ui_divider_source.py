# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Finite lexical UI configuration witness; no SDK identity or runtime effect."""
import ast
import math
import re
from dataclasses import dataclass

NAME = re.compile(r'[A-Za-z_$][A-Za-z0-9_$]*')
NUMBER = re.compile(r'(?:0|[1-9][0-9]*)(?:\.[0-9]+)?')
RESERVED = set('''await break case catch class const continue debugger default delete do else enum
export extends false finally for function if implements import in instanceof
interface let new null package private protected public return static super switch
this throw true try typeof var void while with yield abstract as asserts any async
boolean constructor declare get infer is keyof module namespace never readonly
require number object set string symbol type undefined unique unknown from of struct build'''.split())
SHADOW = {'List', 'divider'}


class Unknown(ValueError):
    pass


class ParsedFrames(dict):
    """Source declaration inventory, not a selection/serving authority."""
    def __init__(self, frames, declared_names):
        super().__init__(frames)
        self.declared_names = tuple(declared_names)


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    start: int
    end: int
    line: int


def quoted(source, start):
    quote = source[start]
    i = start + 1
    while i < len(source):
        c = source[i]
        if c in '\r\n\u2028\u2029':
            raise Unknown('physical string newline')
        if c == quote:
            raw = source[start:i + 1]
            try:
                value = ast.literal_eval(raw)
            except (ValueError, SyntaxError):
                raise Unknown('string escape') from None
            if not isinstance(value, str):
                raise Unknown('not string')
            return i + 1, value
        if c == '\\':
            i += 1
            if i >= len(source) or source[i] in '\r\n\u2028\u2029':
                raise Unknown('string continuation')
            escape = source[i]
            if escape in "\\'\"nrtbfv":
                i += 1
                continue
            if escape == '0' and (i + 1 == len(source) or not source[i + 1].isdigit()):
                i += 1
                continue
            width = {'x': 2, 'u': 4}.get(escape)
            if width and re.fullmatch('[0-9a-fA-F]{' + str(width) + '}', source[i + 1:i + 1 + width]):
                i += width + 1
                continue
            raise Unknown('unsupported string escape')
        i += 1
    raise Unknown('unclosed string')


def tokenize(source, *, declaration_inventory=False):
    if re.search(r'\r(?!\n)', source) or any(c in source for c in ('\u2028', '\u2029')):
        raise Unknown('unsupported physical line separator')
    tokens = []
    i = 0
    line = 1
    while i < len(source):
        c = source[i]
        if c in ' \t\r\n':
            line += c == '\n'
            i += 1
            continue
        if source.startswith('//', i):
            end = source.find('\n', i + 2)
            i = len(source) if end < 0 else end
            continue
        if source.startswith('/*', i):
            end = source.find('*/', i + 2)
            if end < 0:
                raise Unknown('unclosed comment')
            line += source[i:end + 2].count('\n')
            i = end + 2
            continue
        if c in "'\"":
            end, value = quoted(source, i)
            tokens.append(Token('string', value, i, end, line))
        elif NAME.match(source, i):
            match = NAME.match(source, i)
            end = match.end()
            tokens.append(Token('name', match.group(), i, end, line))
        elif c.isascii() and c.isdigit():
            match = re.match(r'[0-9]+(?:\.[0-9]*)?', source[i:])
            value = match.group()
            if not NUMBER.fullmatch(value) or len(value) > 32 or not math.isfinite(float(value)):
                raise Unknown('number')
            end = i + len(value)
            if end < len(source) and (source[end].isalnum() or source[end] in '_$'):
                raise Unknown('number suffix')
            tokens.append(Token('number', value, i, end, line))
        elif source.startswith('=>', i):
            end = i + 2
            tokens.append(Token('punct', '=>', i, end, line))
        elif c in '{}()[]@,:;.=' or (declaration_inventory is True and c in '<>!'):
            end = i + 1
            tokens.append(Token('punct', c, i, end, line))
        else:
            raise Unknown('unsupported active token')
        i = end
    stack = []
    pairs = {}
    for i, token in enumerate(tokens):
        if token.kind != 'punct':
            continue
        if token.value in '([{':
            stack.append(i)
        elif token.value in ')]}':
            if not stack or tokens[stack[-1]].value != {')': '(', ']': '[', '}': '{'}[token.value]:
                raise Unknown('unbalanced tokens')
            opening = stack.pop()
            pairs[opening] = i
    if stack:
        raise Unknown('unclosed tokens')
    return tokens, pairs


def precheck(tokens, pairs):
    closes = {end: start for start, end in pairs.items()}
    for i, token in enumerate(tokens):
        if token.value == '=>' and token.kind == 'punct':
            if not i or i - 1 not in closes or tokens[closes[i - 1]].value != '(':
                raise Unknown('unsupported arrow binding')
            params = tokens[closes[i - 1] + 1:i - 1]
            if (len(params) not in (3, 5) or params[0].kind != 'name'
                    or params[0].value in RESERVED | SHADOW
                    or params[1].kind != 'punct' or params[1].value != ':'
                    or params[2].kind != 'name' or params[2].value not in ('string', 'number', 'boolean')
                    or (len(params) == 5 and (any(t.kind != 'punct' for t in params[3:])
                                             or [t.value for t in params[3:]] != ['[', ']']))):
                raise Unknown('unknown arrow binding')
        if token.kind == 'punct' and token.value == '[':
            end = pairs[i]
            previous = tokens[i - 1] if i else None
            if end > i + 1 and previous and (previous.kind == 'name' or previous.value in (')', ']')):
                raise Unknown('computed/index access')
            if any(t.kind == 'string' and t.value == 'divider' for t in tokens[i + 1:end]):
                raise Unknown('computed divider key')
        if token.kind == 'name' and token.value == 'List':
            if i + 1 >= len(tokens) or tokens[i + 1].value != '(':
                raise Unknown('List binding or unresolved reference')
            if i and tokens[i - 1].value in ('function', 'class', 'struct'):
                raise Unknown('List declaration')
        if token.kind == 'name' and token.value == 'divider':
            if not i or tokens[i - 1].value != '.' or i + 1 >= len(tokens) or tokens[i + 1].value != '(':
                raise Unknown('divider binding or unsupported access')


class Parser:
    def __init__(self, tokens, pairs, start=0, end=None):
        self.t = tokens
        self.pairs = pairs
        self.i = start
        self.end = len(tokens) if end is None else end
        self.bindings = set()
        self.sites = []

    def peek(self, value):
        return self.i < self.end and self.t[self.i].kind != 'string' and self.t[self.i].value == value

    def eat(self, value):
        if not self.peek(value):
            raise Unknown('expected ' + value)
        token = self.t[self.i]
        self.i += 1
        return token

    def maybe(self, value):
        if self.peek(value):
            self.i += 1
            return True
        return False

    def name(self, binding=False):
        if self.i >= self.end or self.t[self.i].kind != 'name':
            raise Unknown('identifier')
        token = self.t[self.i]
        self.i += 1
        if binding:
            if token.value in RESERVED | SHADOW or token.value in self.bindings:
                raise Unknown('reserved, shadow or duplicate binding')
            self.bindings.add(token.value)
        return token

    def scalar(self):
        if self.i >= self.end:
            raise Unknown('scalar')
        token = self.t[self.i]
        if token.kind in ('number', 'string') or token.value in ('true', 'false'):
            self.i += 1
            return
        raise Unknown('scalar')

    def type_name(self):
        if not any(self.peek(x) for x in ('string', 'number', 'boolean')):
            raise Unknown('type')
        self.i += 1
        if self.maybe('['):
            self.eat(']')

    def state(self):
        self.eat('@')
        self.eat('State')
        if self.peek('private') or self.peek('public'):
            self.i += 1
        self.name(binding=True)
        self.eat(':')
        self.type_name()
        self.eat('=')
        if self.maybe('['):
            if not self.peek(']'):
                self.scalar()
                while self.maybe(','):
                    if self.peek(']'):
                        break
                    self.scalar()
            self.eat(']')
        else:
            self.scalar()
        self.maybe(';')

    def argument(self):
        if self.i < self.end and (self.t[self.i].kind in ('string', 'number') or self.peek('true') or self.peek('false')):
            self.scalar()
        else:
            first = self.name().value
            if first in RESERVED and first != 'this':
                raise Unknown('unsupported reference expression')
            while self.maybe('.'):
                self.name()

    def divider(self):
        self.eat('.')
        start = self.eat('divider')
        self.eat('(')
        self.eat('{')
        keys = set()
        width = None
        while True:
            key = self.name().value
            if key in keys or key not in ('strokeWidth', 'color'):
                raise Unknown('property key')
            keys.add(key)
            self.eat(':')
            if key == 'strokeWidth':
                if self.i >= self.end or self.t[self.i].kind != 'number':
                    raise Unknown('width number')
                width = self.t[self.i].value
                self.i += 1
            elif self.i < self.end and self.t[self.i].kind == 'string':
                self.i += 1
            else:
                first = self.name().value
                if first in RESERVED and first != 'this':
                    raise Unknown('unsupported color reference')
                self.eat('.')
                self.name()
            if not self.maybe(',') or self.peek('}'):
                break
        self.eat('}')
        last = self.eat(')')
        if 'strokeWidth' not in keys:
            raise Unknown('missing width')
        self.sites.append(dict(start_line=start.line, end_line=last.line, stroke_width=width))

    def nodes(self):
        while not self.peek('}'):
            if self.i >= self.end:
                raise Unknown('unclosed node body')
            if self.maybe('ForEach'):
                self.eat('(')
                self.eat('this')
                self.eat('.')
                self.name()
                self.eat(',')
                self.eat('(')
                self.name(binding=True)
                self.eat(':')
                self.type_name()
                self.eat(')')
                self.eat('=>')
                self.eat('{')
                self.nodes()
                self.eat('}')
                self.eat(')')
            else:
                name = self.name().value
                if name not in ('List', 'ListItem', 'Text', 'Column', 'Row'):
                    raise Unknown('node constructor')
                self.eat('(')
                args = 0
                if not self.peek(')'):
                    self.argument()
                    args += 1
                    while self.maybe(','):
                        self.argument()
                        args += 1
                self.eat(')')
                block = self.maybe('{')
                if block:
                    self.nodes()
                    self.eat('}')
                if self.peek('.'):
                    if name != 'List' or args or not block:
                        raise Unknown('wrong divider receiver')
                    self.divider()
            self.maybe(';')

    def positive_members(self):
        build = None
        while self.i < self.end:
            if self.peek('@'):
                self.state()
            else:
                if build is not None:
                    raise Unknown('additional member')
                first = self.eat('build')
                self.eat('(')
                self.eat(')')
                self.eat('{')
                self.nodes()
                last = self.eat('}')
                build = (first.line, last.line)
        if build is None or not self.sites:
            raise Unknown('missing build or site')
        return build


def negative_build(tokens, pairs, start, end):
    builds = []
    state = Parser(tokens, pairs, start, end)
    i = start
    while i < end:
        token = tokens[i]
        if token.value == '@':
            state.i = i
            state.state()
            i = state.i
            continue
        if token.kind == 'name' and token.value == 'List':
            raise Unknown('member List declaration')
        if token.kind == 'name' and token.value == 'build':
            if (i + 3 >= end or any(t.kind != 'punct' for t in tokens[i + 1:i + 4])
                    or [t.value for t in tokens[i + 1:i + 4]] != ['(', ')', '{']):
                raise Unknown('unclosed build declaration')
            close = pairs[i + 3]
            builds.append((token.line, tokens[close].line))
            i = close + 1
        else:
            raise Unknown('unknown component member outside build')
    if len(builds) != 1:
        raise Unknown('nonunique build')
    return builds[0]


def parse_ui_divider_file(source, qualified_names):
    """Return exact qualified frame ranges, or None for any unknown source."""
    try:
        if not isinstance(source, str) or not source or isinstance(qualified_names, (str, bytes)):
            return None
        wanted = set(qualified_names)
        if not wanted or any(not isinstance(n, str) or not NAME.fullmatch(n) for n in wanted):
            return None
        tokens, pairs = tokenize(source)
        precheck(tokens, pairs)
        parser = Parser(tokens, pairs)
        seen = set()
        result = {}
        while parser.i < parser.end:
            parser.eat('@')
            if parser.maybe('Entry'):
                parser.eat('@')
            parser.eat('Component')
            parser.maybe('export')
            start = parser.eat('struct')
            name = parser.name(binding=True).value
            if name in seen:
                raise Unknown('duplicate component')
            seen.add(name)
            opening = parser.i
            parser.eat('{')
            close = pairs[opening]
            body_start = parser.i
            body = tokens[body_start:close]
            active = any(t.kind == 'name' and t.value == 'divider' for t in body)
            # A declaration named List at component member level cannot be a call.
            build = negative_build(tokens, pairs, body_start, close)
            sites = []
            if active:
                member = Parser(tokens, pairs, body_start, close)
                build = member.positive_members()
                sites = member.sites
            if name in wanted:
                result[name] = dict(owner_start=start.line, owner_end=tokens[close].line,
                                    build_start=build[0], build_end=build[1], sites=sites,
                                    positive=bool(sites))
            parser.i = close + 1
        return ParsedFrames(result, sorted(seen)) if set(result) == wanted else None
    except (Unknown, TypeError, ValueError, OverflowError, RecursionError):
        return None
