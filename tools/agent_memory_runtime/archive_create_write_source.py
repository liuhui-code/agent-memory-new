# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Closed CREATE/open handle.fd write and same-path unzip syntax, not IO proof."""
from .query_render_source import Token, Unknown, IDENT, Parser, RESERVED as BASE_RESERVED
from .query_recovery_source import KEYWORDS

BAD_LINES = '\v\f\x1c\x1d\x1e\x85\u2028\u2029'
RESERVED = KEYWORDS | BASE_RESERVED | {'of', 'in', 'enum', 'eval', 'arguments', 'package',
                       'unzip', 'Promise', 'Uint8Array', 'UIContext'}


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
                if char not in '{}().,:;=+<>': raise Unknown()
                value = char; pos += 1; kind = 'punct'
        tokens.append(Token(value, kind, start, pos, line))
    tokens.append(Token('', 'eof', len(source), len(source), line))
    return tokens


class ArchiveParser(Parser):
    def __init__(self, source):
        self.source = source; self.tokens = lex(source); self.pos = 0

    def identifier(self):
        token = self.take(kind='ident')
        if token.value in RESERVED: raise Unknown()
        return token

    def seq(self, *values):
        for value in values: self.take(value)

    def separator(self):
        if self.optional(';') or self.peek('}'): return
        prior, current = self.tokens[self.pos - 1:self.pos + 1]
        if '\n' not in self.source[prior.end:current.start]: raise Unknown()

    def declare(self, names):
        value = self.identifier().value
        if value in names: raise Unknown()
        names.add(value)
        return value

    def method(self, fs, owner):
        start = self.take('async'); name = self.identifier()
        if name.line != start.line or name.value in {fs, owner}: raise Unknown()
        names = {fs, owner, name.value}
        self.take('('); first = self.declare(names); self.take(':')
        if self.optional('string'):
            self.take(','); data = self.declare(names); self.seq(':', 'Uint8Array', ',')
            destination = self.declare(names); self.seq(':', 'string'); shape = 'parameters'
        else:
            self.take('UIContext'); shape = 'resource'
        self.seq(')', ':', 'Promise', '<', 'void', '>', '{')
        if shape == 'resource':
            self.take('const'); data = self.declare(names)
            self.seq('=', first, '.', 'resourceManager', '.', 'getRawFileContentSync', '(')
            self.take(kind='string'); self.take(')'); self.separator()
            self.take('const'); path = self.declare(names)
            self.seq('=', first, '.', 'tempDir', '+'); self.take(kind='string'); self.separator()
        else:
            path = first
        self.take('const'); handle = self.declare(names)
        self.seq('=', fs, '.', 'openSync', '(', path, ',', fs, '.', 'OpenMode', '.', 'CREATE', ')')
        self.separator()
        self.seq(fs, '.', 'writeSync', '(', handle, '.', 'fd', ',', data, '.', 'buffer', ')')
        self.separator(); self.seq(fs, '.', 'closeSync', '(', handle, ')'); self.separator()
        self.seq('await', 'unzip', '(', path, ',')
        if shape == 'resource': self.seq(first, '.', 'filesDir')
        else: self.take(destination)
        self.take(')'); self.separator(); end = self.take('}')
        return dict(name=name.value, start_line=start.line, end_line=end.line,
                    shape=shape, path=path, data=data, handle=handle)

    def whole(self):
        self.take('import'); fs = self.identifier().value; self.take('from')
        module = self.take(kind='string')
        if module.value != '@ohos.file.fs': raise Unknown()
        self.separator(); self.optional('export'); start = self.take('class')
        owner = self.identifier().value
        if owner == fs: raise Unknown()
        self.take('{'); methods = []; names = set()
        while not self.peek('}'):
            method = self.method(fs, owner)
            if method['name'] in names: raise Unknown()
            names.add(method['name']); methods.append(method)
        end = self.take('}')
        if self.tokens[self.pos].kind != 'eof' or not methods: raise Unknown()
        return dict(owner=owner, start_line=start.line, end_line=end.line,
                    methods=methods, receiver=fs)


def parse_archive_create_write(source):
    if not isinstance(source, str) or any(c in source for c in BAD_LINES): return None
    try:
        if len(source.encode('utf-8')) > 2 * 1024 * 1024: return None
        return ArchiveParser(source.replace('\r\n', '\n').replace('\r', '\n')).whole()
    except (Unknown, UnicodeError, IndexError):
        return None
