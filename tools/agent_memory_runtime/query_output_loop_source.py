# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Finite direct-loop syntax witness, not runtime or SDK type proof."""
import re
from .query_render_source import Token, Unknown, IDENT
from .query_recovery_source import RecoveryParser, span

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
            elif c in '@{}().,:;=[]<>!':
                value, kind = c, 'punct'
                pos += 1
            else:
                raise Unknown()
        result.append(Token(value, kind, start, pos, line))
    result.append(Token('', 'eof', len(source), len(source), line))
    return result


class OutputParser(RecoveryParser):
    def __init__(self, source):
        self.source=source;self.tokens=lex(source);self.pos=0;self.names=set()

    def identifier(self):
        token=super().identifier()
        if token.value in {'enum','package','eval','arguments'}:raise Unknown()
        return token

    def read(self, receiver):
        self.take(receiver);self.take('.');self.take('readLine');self.take('(');self.take(')')

    def method(self):
        start=self.identifier();self.declare(start.value);self.take('(')
        if self.optional(')'):
            self.take(':');self.take('string');self.take('{');ret=self.take('return')
            value=self.take(kind='string')
            if ret.line!=value.line:raise Unknown()
            self.statement_end();self.take('}')
            return None
        receiver=self.identifier().value;self.take(':');self.identifier();self.take(')')
        self.take(':');self.take('string');self.take('{')
        self.take('const');array=self.identifier().value;self.take(':');self.take('string')
        self.take('[');self.take(']');self.take('=');self.take('[');self.take(']');self.statement_end()
        self.take('let');cursor=self.identifier().value
        if len({receiver,array,cursor})!=3:raise Unknown()
        self.take('=');self.read(receiver);self.statement_end()
        self.take('while');self.take('(');self.take(cursor)
        # !== is one lexical operator, not whitespace-separated punctuators.
        op=[self.take('!'),self.take('='),self.take('=')]
        if op[0].end!=op[1].start or op[1].end!=op[2].start:raise Unknown()
        self.take('null');self.take(')');self.take('{')
        self.take(array);self.take('.');self.take('push');self.take('(');self.take(cursor);self.take(')');self.statement_end()
        self.take(cursor);self.take('=');self.read(receiver);self.statement_end();self.take('}')
        ret=self.take('return');value=self.take(array)
        if ret.line!=value.line:raise Unknown()
        self.take('.');self.take('join');self.take('(')
        self.take(kind='string');self.take(')');self.statement_end();end=self.take('}')
        return dict(name=start.value,**span(start,end))

    def parse(self):
        self.optional('export');start=self.take('class');owner=self.identifier().value;self.take('{')
        methods=[]
        while not self.peek('}'):
            method=self.method()
            if method:methods.append(method)
        end=self.take('}')
        if self.tokens[self.pos].kind!='eof':raise Unknown()
        if not methods:raise Unknown()
        return dict(owner=owner,class_start=start.line,class_end=end.line,methods=methods)


def parse_output_loop_source(source):
    if not isinstance(source,str) or len(source)>2*1024*1024:return None
    # Keep ASI and snapshot line counts within the finite CR/LF grammar.
    if any(c in source for c in '\v\f\x1c\x1d\x1e\x85\u2028\u2029'):return None
    try:return OutputParser(source).parse()
    except (Unknown,IndexError,RecursionError):return None
