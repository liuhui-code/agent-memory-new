# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Closed direct UI background modifier witness; unknown is not absence.

The witness names literal source syntax, never runtime value, overlap causality,
exclusive ownership, or global absence of alternative implementations.
"""
from .query_render_source import Parser, Unknown

UI = {'Column', 'Row', 'Grid', 'GridItem', 'Stack', 'Text', 'TextInput'}


class BackgroundParser(Parser):
    def __init__(self, source):
        super().__init__(source)
        self.nodes = 0
        self.backgrounds = 0

    def declare(self, name):
        if name in UI | {'Color', 'build', 'backgroundColor', 'shadow'}:
            raise Unknown()
        super().declare(name)

    def literal(self, depth=0):
        if depth > 4:
            raise Unknown()
        token = self.tokens[self.pos]
        if token.kind in {'string', 'number'}:
            self.take(kind=token.kind)
        elif self.optional('-'):
            self.take(kind='number')
        elif self.optional('{'):
            keys = set()
            while not self.peek('}'):
                key = self.identifier().value
                if key in keys or len(keys) >= 12:
                    raise Unknown()
                keys.add(key); self.take(':'); self.literal(depth + 1)
                if not self.optional(','):
                    break
            self.take('}')
        else:
            raise Unknown()

    def ui(self, depth=0):
        self.nodes += 1
        if depth > 12 or self.nodes > 64:
            raise Unknown()
        name = self.take(kind='ident').value
        if name not in UI:
            raise Unknown()
        self.take('(')
        if not self.peek(')'):
            self.literal()
        self.take(')')
        if self.optional('{'):
            if name in {'Text', 'TextInput'}:
                raise Unknown()
            while not self.peek('}'):
                self.ui(depth + 1); self.optional(';')
            self.take('}')
        while self.optional('.'):
            prop = self.take(kind='ident').value
            self.take('(')
            self.modifier(prop)
            self.take(')')

    def modifier(self, prop):
        if prop == 'backgroundColor':
            if self.optional('Color'):
                self.take('.'); self.identifier()
            else:
                self.literal()
            self.backgrounds += 1
        elif prop == 'shadow':
            self.literal()
        else:
            raise Unknown()

    def has_witness(self):
        return bool(self.backgrounds)

    def parse(self):
        self.take('@'); self.take('Component')
        self.take('export'); self.take('struct')
        owner = self.identifier().value; self.declare(owner); self.take('{')
        fields = 0
        while not self.peek('build'):
            fields += 1
            if fields > 16:
                raise Unknown()
            if self.optional('@'):
                if self.take(kind='ident').value not in {'State', 'Prop', 'Param'}:
                    raise Unknown()
            field = self.identifier().value; self.declare(field)
            self.take(':')
            if self.take(kind='ident').value not in {'number', 'string', 'boolean'}:
                raise Unknown()
            self.take('=')
            if self.peek('true') or self.peek('false'):
                self.take(kind='ident')
            else:
                self.literal()
            self.separator()
        start = self.take('build').line
        self.take('('); self.take(')'); self.take('{')
        self.ui(); self.optional(';')
        end = self.take('}').line
        self.take('}')
        if self.tokens[self.pos].kind != 'eof' or not self.has_witness():
            raise Unknown()
        return {'owner': owner, 'build_start': start, 'build_end': end}


def parse_background_source(source):
    if not isinstance(source, str) or '\u2028' in source or '\u2029' in source:
        return None
    try:
        if len(source.encode('utf-8')) > 2 * 1024 * 1024:
            return None
        return BackgroundParser(source.replace('\r\n', '\n').replace('\r', '\n')).parse()
    except (Unknown, UnicodeError, IndexError, RecursionError):
        return None
