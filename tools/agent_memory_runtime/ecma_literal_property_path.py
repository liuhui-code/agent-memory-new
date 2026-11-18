# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Bounded literal declaration spelling, never property/call resolution."""
from __future__ import annotations

import re

from .ecma_callback_mask import callback_mask_lines, quoted_end, comment_end

MAX_BYTES = 65536
IDENTIFIER = re.compile(r'[A-Za-z_$][A-Za-z0-9_$]{0,63}\Z')
ROOT = re.compile(r'(?m)^\s*(?:export\s+)?const\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*\{')
TOKEN = re.compile(r'[A-Za-z_$][A-Za-z0-9_$]*|\d+(?:\.\d+)?|=>|\.\.\.|\S')


def _tokens(text):
    result = []
    index = 0
    while index < len(text):
        if text[index].isspace():
            index += 1
            continue
        if text.startswith(('//', '/*'), index):
            end = comment_end(text, index, len(text))
            if end is None:
                raise ValueError('comment')
            index = end
            continue
        if text[index] in "'\"":
            end = quoted_end(text, index, text[index], len(text))
            if end is None:
                raise ValueError('string')
            result.append(('#string', index, end))
            index = end
            continue
        match = TOKEN.match(text, index)
        result.append((match.group(), index, match.end()))
        index = match.end()
    return result


class _Object:
    def __init__(self, text, tokens):
        self.text, self.tokens = text, tokens
        self.entries = 0
        self.paths = []

    def balanced(self, i, opening, closing):
        depth = 1
        i += 1
        while i < len(self.tokens):
            token = self.tokens[i][0]
            if token == opening:
                depth += 1
            elif token == closing:
                depth -= 1
                if not depth:
                    return i + 1
            i += 1
        raise ValueError('unclosed')

    def object(self, i, chain):
        if len(chain) > 8 or self.tokens[i][0] != '{':
            raise ValueError('depth')
        i += 1
        seen = set()
        while i < len(self.tokens) and self.tokens[i][0] != '}':
            key, start, _ = self.tokens[i]
            self.entries += 1
            if self.entries > 256 or IDENTIFIER.fullmatch(key) is None or key in seen:
                raise ValueError('key')
            seen.add(key)
            if self.tokens[i + 1][0] != ':':
                raise ValueError('property')
            i += 2
            value = self.tokens[i][0]
            if value == '{':
                i = self.object(i, [*chain, key])
            elif value == '(' or value == 'async':
                if value == 'async':
                    i += 1
                if self.tokens[i][0] != '(':
                    raise ValueError('callback')
                i = self.balanced(i, '(', ')')
                # Only the already supported unannotated block arrow shape here.
                if self.tokens[i][0] != '=>' or self.tokens[i + 1][0] != '{':
                    raise ValueError('arrow')
                i = self.balanced(i + 1, '{', '}')
                line = self.text.count('\n', 0, start) + 1
                end = self.text.count('\n', 0, self.tokens[i - 1][1]) + 1
                path = [*chain, key]
                if len(path) > 8:
                    raise ValueError('segments')
                if len(path) >= 3:
                    self.paths.append(((line, end, key), '.'.join(path)))
            elif value == '#string' or value in {'true', 'false', 'null'} or re.fullmatch(r'\d+(?:\.\d+)?', value):
                i += 1
            else:
                raise ValueError('unknown value')
            if self.tokens[i][0] == ',':
                i += 1
            elif self.tokens[i][0] != '}':
                raise ValueError('delimiter')
        if i >= len(self.tokens):
            raise ValueError('unclosed object')
        return i + 1


def literal_property_paths(text):
    if not isinstance(text, str) or len(text.encode('utf-8')) > MAX_BYTES:
        return {}
    # Preserve LF coordinates; unknown masks or templates decline optional facts.
    text = text.replace('\r\n', '\n')
    if any(char in text for char in ('\r', '\v', '\f', '\x85', '\u2028', '\u2029')):
        return {}
    lines = text.split('\n')
    mask = callback_mask_lines(lines)
    if mask is None or '`' in text:
        return {}
    masked = '\n'.join(mask)
    matches = list(ROOT.finditer(masked))
    if len(matches) > 256:
        return {}
    names = [m.group(1) for m in matches]
    try:
        tokens = _tokens(text)
    except ValueError:
        return {}
    positions = {start: index for index, (_value, start, _end) in enumerate(tokens)}
    result = {}
    for match in matches:
        name = match.group(1)
        if names.count(name) != 1 or IDENTIFIER.fullmatch(name) is None:
            continue
        opening = masked.find('{', match.start(), match.end())
        try:
            parser = _Object(text, tokens)
            parser.object(positions[opening], [name])
            starts = [key[0] for key, _ in parser.paths]
            for key, path in parser.paths:
                if starts.count(key[0]) == 1:
                    result[key] = path
        except (ValueError, IndexError, KeyError):
            continue
    return result


def admitted_mapping(rows, entities, target, entity, project_id, digest, adapter):
    """Qualify the existing mapper's assignment, without choosing another row."""
    fields = ('symbol_key', 'qualified_name', 'signature', 'start_line',
              'end_line', 'semantic_adapter')
    if not rows or len(rows) != len(entities) or not digest:
        return False
    if any(e.kind != 'function' or e.signature != f'callback {e.name}@{e.start_line}'
           or e.file_path != entity.file_path or e.name != entity.name for e in entities):
        return False
    ranges = {(e.start_line, e.end_line): e for e in entities}
    if (len(ranges) != len(entities) or len({e.key for e in entities}) != len(entities)
            or len({e.start_line for e in entities}) != len(entities)):
        return False
    generation = target['index_generation']
    if type(generation) is not int or generation <= 0:
        return False
    if (len({r['id'] for r in rows}) != len(rows)
            or any(type(r['id']) is not int or r['id'] <= 0
                   or r['project_id'] != project_id or r['file_path'] != entity.file_path
                   or r['symbol'] != entity.name or r['symbol_type'] != 'function'
                   or r['source_digest'] != digest or r['index_generation'] != generation
                   for r in rows)):
        return False
    if all(all(r[k] is None for k in fields) for r in rows):
        return True  # Atomic UPDATE supplies this entity's identity AND spelling.
    seen = set()
    for row in rows:
        start, end = row['start_line'], row['end_line']
        if type(start) is not int or type(end) is not int or start <= 0 or end < start:
            return False
        bounds = (start, end)
        expected = ranges.get(bounds)
        if expected is None or bounds in seen:
            return False
        seen.add(bounds)
        for key, value in (('symbol_key', expected.key), ('qualified_name', expected.qualified_name),
                           ('signature', expected.signature), ('semantic_adapter', adapter)):
            if row[key] is not None and row[key] != value:
                return False
    return (target['start_line'], target['end_line']) == (entity.start_line, entity.end_line)
