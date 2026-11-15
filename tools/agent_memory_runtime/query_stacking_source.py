# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Direct Stack syntax, not event behavior, overlap cause or exhaustive owners."""
from .query_background_source import BackgroundParser, UI
from .query_render_source import lex, Unknown

STRICT_BINDING_RESERVED = set(
    "enum implements interface package private protected public static eval arguments".split())
EXTRA_LINE_SEPARATORS = "\v\f\x1c\x1d\x1e\x85\u2028\u2029"


class StackingParser(BackgroundParser):
    def __init__(self, source):
        # Arrow lexing is local opt-in; older cleanup/background syntax is unchanged.
        self.source = source
        self.tokens = lex(source, allow_arrow=True)
        self.pos = 0
        self.names = set()
        self.methods = {}
        self.constructors = set()
        self.nodes = self.backgrounds = self.stacks = 0

    def ui(self, depth=0):
        if self.peek('Stack'):
            self.stacks += 1
        super().ui(depth)

    def modifier(self, prop):
        if prop != 'onTouch':
            return super().modifier(prop)
        self.take('(')
        if not self.peek(')'):
            param = self.identifier().value
            if param in UI | {'Color', 'build'} | STRICT_BINDING_RESERVED:
                raise Unknown()
            if self.optional(':'):
                self.identifier()
        parameter_end = self.take(')')
        arrow = self.take('=>')
        if '\n' in self.source[parameter_end.end:arrow.start]:
            raise Unknown()
        self.take('{')
        count = 0
        while not self.peek('}'):
            count += 1
            if count > 8:
                raise Unknown()
            self.take('this'); self.take('.'); self.identifier()
            self.take('('); self.take(')')
            if not self.peek('}'):
                self.separator()
            else:
                self.optional(';')
        self.take('}')

    def has_witness(self):
        return bool(self.stacks)


def parse_stacking_source(source):
    if not isinstance(source, str) or any(char in source for char in EXTRA_LINE_SEPARATORS):
        return None
    try:
        if len(source.encode('utf-8')) > 2 * 1024 * 1024:
            return None
        return StackingParser(source.replace('\r\n', '\n').replace('\r', '\n')).parse()
    except (Unknown, UnicodeError, IndexError, RecursionError):
        return None


def parse_visual_alternative_source(source):
    from .query_background_source import parse_background_source
    if not isinstance(source, str) or any(char in source for char in EXTRA_LINE_SEPARATORS):
        return None
    return parse_background_source(source) or parse_stacking_source(source)
