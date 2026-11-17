"""Closed callback-bound indexed read; no SDK identity or runtime safety proof."""
import re
from .ui_divider_source import tokenize, Unknown, RESERVED

SHADOW = {'Stack', 'Text', 'TouchEvent', 'onTouch'}


class Parser:
    def __init__(self, source):
        self.tokens, self.pairs = tokenize(source)
        self.i = 0

    def eat(self, value):
        if self.i >= len(self.tokens):
            raise Unknown('unexpected end')
        token = self.tokens[self.i]
        if token.kind == 'string' or token.value != value:
            raise Unknown('unexpected token')
        self.i += 1
        return token

    def maybe(self, value):
        if self.i < len(self.tokens) and self.tokens[self.i].kind != 'string' and self.tokens[self.i].value == value:
            return self.eat(value)
        return None

    def ident(self):
        if self.i >= len(self.tokens):
            raise Unknown('identifier')
        token = self.tokens[self.i]
        if token.kind != 'name' or token.value in RESERVED | SHADOW:
            raise Unknown('reserved or shadow binding')
        self.i += 1
        return token

    def end_statement(self, previous):
        if self.maybe(';'):
            return
        if self.i < len(self.tokens):
            following = self.tokens[self.i]
            if following.value == '}' or following.line > previous.line:
                return
        raise Unknown('statement separator')

    def component(self):
        self.eat('@')
        if self.maybe('Entry'):
            self.eat('@')
        self.eat('Component')
        self.maybe('export')
        start = self.eat('struct'); owner = self.ident().value; self.eat('{')
        if self.maybe('@'):
            self.eat('State')
        field = self.ident().value; self.eat(':'); self.eat('number'); self.eat('=')
        zero = self.eat('0')
        if zero.kind != 'number':
            raise Unknown('initializer')
        self.end_statement(zero)
        build = self.eat('build'); self.eat('('); self.eat(')'); self.eat('{')
        self.eat('Stack'); self.eat('('); self.eat(')'); self.eat('{')
        if self.maybe('Text'):
            self.eat('(')
            if self.i >= len(self.tokens) or self.tokens[self.i].kind != 'string':
                raise Unknown('inert text')
            self.i += 1; self.eat(')'); self.maybe(';')
        self.eat('}'); self.eat('.')
        callback = self.eat('onTouch'); self.eat('('); self.eat('(')
        parameter = self.ident().value; self.eat(':'); self.eat('TouchEvent')
        self.eat(')'); self.eat('=>'); self.eat('{'); self.eat('const')
        local = self.ident().value
        if local == parameter:
            raise Unknown('shadow parameter')
        self.eat('='); self.eat(parameter); self.eat('.'); self.eat('touches'); self.eat('[')
        if self.i >= len(self.tokens):
            raise Unknown('literal index')
        index = self.tokens[self.i]
        if index.kind != 'number' or re.fullmatch(r'0|[1-9][0-9]*', index.value, re.ASCII) is None:
            raise Unknown('noncanonical index')
        self.i += 1; bracket = self.eat(']'); self.end_statement(bracket)
        self.eat('this'); self.eat('.'); self.eat(field); self.eat('=')
        self.eat(local); self.eat('.'); consumer = self.eat('x'); self.end_statement(consumer)
        close = self.eat('}'); self.eat(')'); self.maybe(';')
        build_end = self.eat('}'); owner_end = self.eat('}')
        return owner, dict(owner=owner, owner_start=start.line, owner_end=owner_end.line,
                           build_start=build.line, build_end=build_end.line,
                           callback_name='onTouch', callback_start=callback.line, callback_end=close.line,
                           callback_start_offset=callback.start, callback_end_offset=close.end,
                           literal_index=int(index.value), parameter=parameter, local=local, field=field)


def parse_touch_index_file(source):
    """Full-file certificate map or None (unknown), never an absence certificate."""
    if type(source) is not str:
        return None
    try:
        parser = Parser(source); result = {}
        while parser.i < len(parser.tokens):
            owner, proof = parser.component()
            if owner in result:
                return None
            result[owner] = proof
        return result or None
    except (Unknown, ValueError, TypeError, KeyError, IndexError, OverflowError):
        return None
