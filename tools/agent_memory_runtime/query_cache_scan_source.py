# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Closed minimum-field scan/delete syntax, not timestamp or runtime proof."""
import re
from .query_render_source import Token, Unknown

_REQUEST = re.compile(
    r'(?:Locate|Find|Return) executable eviction scan ownership when a cache '
    r'remains above its entry limit\.?', re.I | re.ASCII)
_IDENT = re.compile(r'[A-Za-z_$][A-Za-z0-9_$]*', re.ASCII)
_RESERVED = set(('if else for while do switch case default try catch finally with '
    'function class return throw new delete void typeof instanceof in of yield await '
    'import export const let var break continue debugger super this async get set '
    'constructor true false null undefined struct extends enum implements interface '
    'package private protected public static eval arguments Map Number Date string '
    'number boolean any unknown never readonly declare abstract namespace type').split())
_BAD_LINES = '\v\f\x1c\x1d\x1e\x85\u2028\u2029'


def cache_scan_request(query):
    return bool(isinstance(query, str) and len(query) <= 240 and _REQUEST.fullmatch(query))


def _lex(source):
    result = []
    pos = 0
    line = 1
    while pos < len(source):
        char = source[pos]
        if char in ' \t\n':
            line += char == '\n'; pos += 1
            continue
        if source.startswith('//', pos):
            end = source.find('\n', pos + 2)
            pos = len(source) if end < 0 else end
            continue
        if source.startswith('/*', pos):
            end = source.find('*/', pos + 2)
            if end < 0:
                raise Unknown()
            line += source.count('\n', pos, end + 2); pos = end + 2
            continue
        start = pos
        match = _IDENT.match(source, pos)
        if match:
            value = match.group(); pos = match.end(); kind = 'ident'
        else:
            value = next((op for op in ('!==', '<=') if source.startswith(op, pos)), None)
            if value is None:
                if char not in '{}()[].,:;=<>|':
                    raise Unknown()
                value = char
            pos += len(value); kind = 'punct'
        result.append(Token(value, kind, start, pos, line))
    result.append(Token('', 'eof', len(source), len(source), line))
    return result


class _Parser:
    def __init__(self, source):
        self.source = source
        self.tokens = _lex(source)
        self.pos = 0

    def peek(self, value):
        return self.tokens[self.pos].value == value

    def take(self, value):
        token = self.tokens[self.pos]
        if token.kind == 'eof' or token.value != value:
            raise Unknown()
        self.pos += 1
        return token

    def seq(self, *values):
        for value in values:
            self.take(value)

    def optional(self, value):
        if self.peek(value):
            self.take(value)
            return True
        return False

    def name(self):
        token = self.tokens[self.pos]
        if token.kind != 'ident' or token.value in _RESERVED:
            raise Unknown()
        self.pos += 1
        return token

    def separator(self):
        if self.optional(';') or self.peek('}'):
            return
        previous, current = self.tokens[self.pos - 1:self.pos + 1]
        if '\n' not in self.source[previous.end:current.start]:
            raise Unknown()

    def receiver(self, field):
        self.seq('this', '.', field)

    def parse(self):
        self.optional('export')
        class_start = self.take('class').line
        owner = self.name().value
        self.take('{'); self.take('private')
        field = self.name().value
        self.seq(':', 'Map', '<', 'string', ',')
        entry = self.name().value
        self.seq('>', '=', 'new', 'Map', '(', ')'); self.separator()
        method = self.name()
        self.take('('); limit = self.name().value
        self.seq(':', 'number', ')', ':', 'void', '{', 'if', '(')
        self.receiver(field); self.seq('.', 'size', '<=', limit, ')', '{', 'return')
        self.separator(); self.take('}')
        self.take('let'); selected = self.name().value
        self.seq(':', 'string', '|', 'undefined', '=', 'undefined'); self.separator()
        self.take('let'); minimum = self.name().value
        self.seq('=', 'Number', '.', 'MAX_SAFE_INTEGER'); self.separator()
        self.seq('for', '(', 'const', '['); key = self.name().value
        self.take(','); value = self.name().value
        self.seq(']', 'of'); self.receiver(field); self.seq(')', '{', 'if', '(', value, '.')
        member = self.name().value
        self.seq('<', minimum, ')', '{', minimum, '=', value, '.', member); self.separator()
        self.seq(selected, '=', key); self.separator()
        self.seq('}', '}', 'if', '(', selected, '!==', 'undefined', ')', '{')
        self.receiver(field); self.seq('.', 'delete', '(', selected, ')'); self.separator()
        self.take('}'); end = self.take('}').line
        class_end = self.take('}').line
        if (self.tokens[self.pos].kind != 'eof' or owner == entry or field == method.value
                or len({limit, selected, minimum, key, value}) != 5):
            raise Unknown()
        return dict(owner=owner, class_start=class_start, class_end=class_end,
                    method=method.value, start_line=method.line, end_line=end)


def parse_cache_scan_source(source):
    if not isinstance(source, str) or any(char in source for char in _BAD_LINES):
        return None
    try:
        if len(source.encode('utf-8')) > 2 * 1024 * 1024:
            return None
        return _Parser(source.replace('\r\n', '\n').replace('\r', '\n')).parse()
    except (Unknown, UnicodeError, IndexError):
        return None
