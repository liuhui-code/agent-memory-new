"""Finite direct local loop/result syntax for retrieval, not runtime authority."""
import re
from .query_render_source import Token, Unknown, IDENT, Parser
from .query_recovery_source import KEYWORDS

BAD_LINES = '\v\f\x1c\x1d\x1e\x85\u2028\u2029'
RESERVED = KEYWORDS | {'of', 'in', 'eval', 'arguments', 'enum', 'package'}


def lex(source):
    tokens = []; pos = 0; line = 1
    while pos < len(source):
        char = source[pos]
        if char in ' \t\n':
            line += char == '\n'; pos += 1; continue
        if source.startswith('//', pos):
            end = source.find('\n', pos + 2)
            pos = len(source) if end < 0 else end; continue
        if source.startswith('/*', pos):
            end = source.find('*/', pos + 2)
            if end < 0: raise Unknown()
            line += source.count('\n', pos, end + 2); pos = end + 2; continue
        start = pos
        if char in "'\"":
            quote = char; parts = []; pos += 1
            while pos < len(source) and source[pos] != quote:
                value = source[pos]
                if value in '\r\n': raise Unknown()
                if value == '\\':
                    pos += 1
                    if pos >= len(source) or source[pos] not in "'\"\\n": raise Unknown()
                    value = '\n' if source[pos] == 'n' else source[pos]
                parts.append(value); pos += 1
            if pos >= len(source): raise Unknown()
            pos += 1; value = ''.join(parts); kind = 'string'
        else:
            match = IDENT.match(source, pos)
            if match:
                value = match.group(); pos = match.end(); kind = 'ident'
            else:
                value = next((v for v in ('===', '+=') if source.startswith(v, pos)), None)
                if value is None:
                    if char not in '{}()[].,:;=+': raise Unknown()
                    value = char
                pos += len(value); kind = 'punct'
        tokens.append(Token(value, kind, start, pos, line))
    tokens.append(Token('', 'eof', len(source), len(source), line))
    return tokens


class LoopParser(Parser):
    def __init__(self, source):
        self.source = source; self.tokens = lex(source); self.pos = 0

    def identifier(self):
        token = self.take(kind='ident')
        if token.value in RESERVED: raise Unknown()
        return token

    def seq(self, *values):
        for value in values: self.take(value)

    def end_statement(self):
        if self.optional(';') or self.peek('}'): return
        prior, current = self.tokens[self.pos - 1:self.pos + 1]
        # Only the next grammar statement may start across a physical newline.
        if current.value not in {'for', 'return'} or '\n' not in self.source[prior.end:current.start]:
            raise Unknown()

    def item_value(self, item):
        if self.optional('this'):
            self.take('.'); self.identifier(); self.seq('(', item, '.')
            self.identifier(); self.take(')')
        else:
            self.take(item)
            if self.optional('.'): self.identifier()

    def assignment(self, output, item):
        self.take(output)
        if self.optional('+='):
            mode = 'append'; self.item_value(item)
        else:
            self.take('=')
            if self.optional(output):
                self.take('+'); mode = 'append'
            else: mode = 'overwrite'
            self.item_value(item)
        self.end_statement()
        return mode

    def method(self):
        start = self.identifier(); name = start.value; self.take('(')
        if self.optional(')'):
            self.seq(':', 'string', '{'); ret = self.take('return'); value = self.take(kind='string')
            if ret.line != value.line: raise Unknown()
            self.end_statement(); end = self.take('}')
            return dict(name=name, start_line=start.line, end_line=end.line, positive=False)
        parameter = self.identifier().value; self.take(':')
        if not self.optional('string'): self.identifier()
        self.seq('[', ']', ')', ':', 'string', '{', 'let')
        output = self.identifier().value
        if self.optional(':'): self.take('string')
        self.take('='); self.take(kind='string'); self.end_statement()
        self.seq('for', '(', 'const'); item = self.identifier().value
        if len({parameter, output, item}) != 3: raise Unknown()
        self.seq('of', parameter, ')', '{')
        modes = []
        if self.optional('if'):
            self.seq('(', item, '.'); self.identifier(); self.take('==='); self.take(kind='string')
            self.seq(')', '{'); modes.append(self.assignment(output, item))
            self.seq('}', 'else', '{'); modes.append(self.assignment(output, item)); self.take('}')
        else: modes.append(self.assignment(output, item))
        self.take('}'); ret = self.take('return'); value = self.take(output)
        if ret.line != value.line: raise Unknown()
        self.end_statement(); end = self.take('}')
        return dict(name=name, start_line=start.line, end_line=end.line, positive=True,
                    update_form='append' if set(modes) == {'append'} else 'overwrite',
                    parameter=parameter, item=item, output=output)

    def whole_class(self):
        self.optional('export'); start = self.take('class'); owner = self.identifier().value
        self.take('{'); methods = []; names = set()
        while not self.peek('}'):
            method = self.method()
            if method['name'] in names: raise Unknown()
            names.add(method['name']); methods.append(method)
        end = self.take('}')
        if self.tokens[self.pos].kind != 'eof' or not any(m['positive'] for m in methods):
            raise Unknown()
        return dict(owner=owner, start_line=start.line, end_line=end.line,
                    methods=[m for m in methods if m['positive']])


def parse_record_loop(source, *, whole_class=False):
    if not isinstance(source, str) or any(c in source for c in BAD_LINES): return None
    try:
        if len(source.encode('utf-8')) > 2 * 1024 * 1024: return None
        parser = LoopParser(source.replace('\r\n', '\n').replace('\r', '\n'))
        result = parser.whole_class() if whole_class else parser.method()
        if parser.tokens[parser.pos].kind != 'eof': return None
        return result if whole_class or result['positive'] else None
    except (Unknown, UnicodeError, IndexError):
        return None
