# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

"""Private conservative removal evidence, not a complete ECMAScript lexer."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class NoncodeScan:
    noncode: bytes
    unknown_start: int | None


def confirmed_noncode(text: str) -> NoncodeScan:
    flags = bytearray(len(text))
    index = 0
    while index < len(text):
        char = text[index]
        if text.startswith('//', index):
            end = text.find('\n', index + 2)
            end = len(text) if end < 0 else end
        elif text.startswith('/*', index):
            close = text.find('*/', index + 2)
            if close < 0:
                return NoncodeScan(bytes(flags), index)
            end = close + 2
        elif char in "'\"`":
            end = closed_literal_end(text, index)
            if end is None:
                return NoncodeScan(bytes(flags), index)
        elif char in '/<':
            # No regex/division or JSX/type-expression grammar is inferred.
            # This ambiguity is sticky: later quotes cannot regain certainty.
            return NoncodeScan(bytes(flags), index)
        else:
            index += 1
            continue
        flags[index:end] = b'\x01' * (end - index)
        index = end
    return NoncodeScan(bytes(flags), None)


def closed_literal_end(text: str, start: int) -> int | None:
    quote = text[start]
    index = start + 1
    while index < len(text):
        char = text[index]
        if char == '\\':
            index += 2
            continue
        if char == quote:
            return index + 1
        if quote == '`' and text.startswith('${', index):
            # Interpolated templates are deliberately unsupported, from opener.
            return None
        if quote != '`' and char in '\r\n':
            return None
        index += 1
    return None


def confirmed_noncode_lines(lines: list[str]) -> list[bytes]:
    text = '\n'.join(lines)
    scan = confirmed_noncode(text)
    result = []
    offset = 0
    for line in lines:
        result.append(scan.noncode[offset:offset + len(line)])
        offset += len(line) + 1
    return result
