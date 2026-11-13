# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Equal-position callback admission mask, not a complete ECMAScript lexer.

Template interpolation is opaque/unsupported, never evidence of absent operations.
Unknown lexical syntax returns None: callers preserve the complete legacy ranges.
"""
from .source_call_scanner import code_mask

MAX_TEMPLATE_CHARS = 65536


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


def template_end(text, start, stop):
    index = start + 1
    while index < stop:
        if text[index] == '\\':
            index += 2
        elif text[index] == '`':
            return index + 1
        elif text.startswith('${', index):
            # Interpolation contains executable source. Do not hide its callbacks.
            return None
        else:
            index += 1
    return None


def callback_mask_lines(lines):
    text = '\n'.join(lines)
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
            end = template_end(text, index, min(len(text), index + MAX_TEMPLATE_CHARS))
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
