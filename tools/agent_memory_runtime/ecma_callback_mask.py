# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Equal-position callback admission mask, not a complete ECMAScript lexer.

Template interpolation is opaque by default, never evidence of absent operations.
Operation-only opt-in admits reference-shaped spelling, not effect purity.
Unknown lexical syntax returns None: callers preserve the complete legacy ranges.
"""
import re

from .source_call_scanner import code_mask

MAX_TEMPLATE_CHARS = 65536
REFERENCE_BODY = re.compile(
    r"[ \t\r\n]*[A-Za-z_$][A-Za-z0-9_$]*"
    r"(?:[ \t\r\n]*\.[ \t\r\n]*[A-Za-z_$][A-Za-z0-9_$]*)*[ \t\r\n]*"
)


def quoted_end(text, start, quote, stop):
    index = start + 1
    while index < stop:
        if text[index] == '\\':
            index += 2
        elif text[index] == quote:
            return index + 1
        else:
            index += 1
    return None


def comment_end(text, start, stop):
    if text.startswith('//', start):
        end = text.find('\n', start + 2, stop)
        return stop if end < 0 else end + 1
    if text.startswith('/*', start):
        end = text.find('*/', start + 2, stop)
        return None if end < 0 else end + 2
    return None


def template_end(text, start, stop, *, allow_reference_interpolation=False):
    index = start + 1
    while index < stop:
        if text[index] == '\\':
            index += 2
        elif text[index] == '`':
            return index + 1
        elif text.startswith('${', index):
            # Opt-in recognizes spelling only, not absence of getter/coercion effects.
            if not allow_reference_interpolation:
                return None
            end = text.find('}', index + 2, stop)
            if end < 0 or REFERENCE_BODY.fullmatch(text[index + 2:end]) is None:
                return None
            index = end + 1
            continue
        else:
            index += 1
    return None


def callback_mask_lines(lines, *, allow_reference_interpolation=False):
    # Both semantic splitlines() and excerpt readlines() supply one item per
    # physical line. Do not introduce an extra line for retained terminators.
    text = '\n'.join(line.rstrip('\r\n') for line in lines)
    masked = list(text)
    index = 0
    while index < len(text):
        char = text[index]
        if char in "'\"":
            index = quoted_end(text, index, char, len(text))
            if index is None:
                return None
        elif text.startswith(('//', '/*'), index):
            index = comment_end(text, index, len(text))
            if index is None:
                return None
        elif char == '/':
            # Do not guess regex versus division, or let quotes in regex poison
            # the following source. Preserve legacy behavior for this file.
            return None
        elif char == '`':
            end = template_end(
                text, index, min(len(text), index + MAX_TEMPLATE_CHARS),
                allow_reference_interpolation=allow_reference_interpolation,
            )
            if end is None:
                return None
            masked[index:end] = [' '] * (end - index)
            index = end
        else:
            index += 1
    # Template syntax must be opaque BEFORE the ordinary quote scanner runs.
    masked = list(code_mask(''.join(masked)))
    # code_mask intentionally masks comment newlines; restore original positions.
    for index, char in enumerate(text):
        if char == '\n':
            masked[index] = '\n'
    return ''.join(masked).split('\n')
