# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Finite local clock-field scan witness; not runtime eviction correctness."""
from .query_cache_scan_source import _Parser, _BAD_LINES
from .query_render_source import Unknown


class ClockScanParser(_Parser):
    def parse(self):
        self.optional('export'); self.take('interface'); entry = self.name().value
        self.take('{'); clock = self.name().value
        self.seq(':', 'number'); self.separator(); payload = self.name().value
        self.seq(':', 'string'); self.separator(); self.take('}')
        self.optional('export'); class_start = self.take('class').line
        owner = self.name().value; self.seq('{', 'private'); field = self.name().value
        self.seq(':', 'Map', '<', 'string', ',', entry, '>', '=', 'new', 'Map', '(', ')')
        self.separator(); self.seq('constructor', '(', 'private'); capacity = self.name().value
        self.seq(':', 'number', ')', '{', '}'); self.optional(';')
        method = self.name(); self.take('('); argument = self.name().value
        self.seq(':', 'string', ','); valuearg = self.name().value
        self.seq(':', 'string', ')', ':', 'void', '{')
        write_line = self.tokens[self.pos].line
        self.receiver(field); self.seq('.', 'set', '(', argument, ',', '{', clock, ':', 'Date', '.', 'now', '(', ')', ',', payload, ':', valuearg, '}', ')')
        self.separator(); capacity_line = self.take('if').line
        self.take('('); self.receiver(field); self.seq('.', 'size', '<=', 'this', '.', capacity, ')', '{', 'return')
        self.separator(); self.take('}'); self.take('let'); selected = self.name().value
        self.seq(':', 'string', '|', 'undefined', '=', 'undefined'); self.separator()
        self.take('let'); minimum = self.name().value
        self.seq(':', 'number', '=', 'Number', '.', 'MAX_SAFE_INTEGER'); self.separator()
        loop_line = self.take('for').line; self.seq('(', 'const', '['); key = self.name().value
        self.take(','); value = self.name().value; self.seq(']', 'of'); self.receiver(field)
        self.seq(')', '{'); compare_line = self.take('if').line
        self.seq('(', value, '.', clock, '<', minimum, ')', '{', minimum, '=', value, '.', clock)
        self.separator(); key_line = self.tokens[self.pos].line
        self.seq(selected, '=', key); self.separator(); self.seq('}', '}', 'if', '(', selected, '!==', 'undefined', ')', '{')
        delete_line = self.tokens[self.pos].line
        self.receiver(field); self.seq('.', 'delete', '(', selected, ')'); self.separator()
        self.take('}'); end = self.take('}').line; class_end = self.take('}').line
        if (self.tokens[self.pos].kind != 'eof' or owner == entry or clock == payload
                or len({field, capacity, method.value}) != 3
                or len({argument, valuearg, selected, minimum, key, value}) != 6):
            raise Unknown()
        return dict(owner=owner, method=method.value, class_start=class_start,
                    class_end=class_end, start_line=method.line, end_line=end,
                    relation_lines=[write_line, capacity_line, loop_line, compare_line, key_line, delete_line],
                    field=clock, collection=field)


def parse_clock_scan(source):
    if type(source) is not str or any(c in source for c in _BAD_LINES): return None
    try:
        if len(source.encode('utf-8')) > 2 * 1024 * 1024: return None
        return ClockScanParser(source.replace('\r\n', '\n').replace('\r', '\n')).parse()
    except (Unknown, UnicodeError, IndexError):
        return None
