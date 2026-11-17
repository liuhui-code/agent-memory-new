# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Validation-local lexical extension; original offsets, no source rewriting.

Ordinary scanning mirrors the shared finite tokenizer; its consumers are unchanged.
Template recognition is lexical only. The validation parser supplies the sole
auxiliary-console/string-parameter permission; no template grants a fact.
"""
import math
import re
from .ui_divider_source import NAME, NUMBER, Token, Unknown, quoted, tokenize


def template(source, start):
    end = source.find('`', start + 1)
    if end < 0:
        raise Unknown('unclosed auxiliary template')
    match = re.fullmatch(r'(.*?)\$\{([A-Za-z_$][A-Za-z0-9_$]*)\}(.*)', source[start + 1:end])
    if not match:
        raise Unknown('auxiliary template interpolation')
    before, name, after = match.groups()
    for chunk in (before, after):
        if any(not 32 <= ord(c) <= 126 or c in '`\\${}' for c in chunk):
            raise Unknown('auxiliary template literal chunk')
    return end + 1, name


def tokenize_validation(source):
    if "`" not in source:
        return tokenize(source, declaration_inventory=True)
    declaration_inventory = True
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
        elif c == '`':
            end, name = template(source, i)
            tokens.append(Token('template', source[i:end], i, end, line))
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

