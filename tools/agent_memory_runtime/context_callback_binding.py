# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

"""Read-only, budget-bounded context for a callback and its scalar siblings."""
from __future__ import annotations
import re
from typing import Any
from .source_call_scanner import code_mask
from .ecma_callable_ranges import property_callback_ranges, PROPERTY_CALLBACK_RE

_NAME = r'[A-Za-z_$][\w$]*'
_SCALAR = re.compile(r'''(?:'(?:\\.|[^'\\\r\n])*'|"(?:\\.|[^"\\\r\n])*"|(?:true|false|null)|-?(?:\d+(?:\.\d+)?)(?:[eE][+-]?\d+)?)''')


def _pairs(mask: str) -> dict[int, int] | None:
    stack: list[tuple[str, int]] = []
    result: dict[int, int] = {}
    closes = {')': '(', ']': '[', '}': '{'}
    for index, char in enumerate(mask):
        if char in '([{':
            stack.append((char, index))
        elif char in closes:
            if not stack or stack[-1][0] != closes[char]:
                return None
            _, start = stack.pop()
            result[start] = index
    return None if stack else result


def _object_open(mask: str, opening: int, pairs: dict[int, int]) -> bool:
    prefix = mask[:opening].rstrip()
    if not prefix:
        return False
    if prefix.endswith('['):
        return True
    if prefix.endswith(','):
        parents = [start for start, end in pairs.items() if start < opening < end]
        return bool(parents) and mask[max(parents)] == '['
    line = mask[:opening].rsplit('\n', 1)[-1]
    if re.search(r'\breturn[ \t]*$', line):
        return True
    return bool(re.fullmatch(r'\s*(?:export\s+)?(?:const|let|var)\s+' + _NAME + r'(?:\s*:\s*[\w.<>, \[\]]+)?\s*=\s*', line))


def _members(mask: str, opening: int, closing: int, pairs: dict[int, int]) -> list[tuple[int, int]]:
    result: list[tuple[int, int]] = []
    start = index = opening + 1
    while index < closing:
        if index in pairs:
            index = pairs[index] + 1
            continue
        if mask[index] == ',':
            result.append((start, index))
            start = index + 1
        index += 1
    if mask[start:closing].strip():
        result.append((start, closing))
    return result


def binding_context_range(path_suffix: str, source_lines: list[str], source_range: dict[str, Any],
                          max_lines: int, char_budget: int) -> dict[str, Any] | None:
    if path_suffix.casefold() not in {'.ets', '.ts', '.js'} or source_range.get('selection_reason') != 'ecma_property_callback_window':
        return None
    start, end = source_range.get('start_line'), source_range.get('end_line')
    if type(start) is not int or type(end) is not int or not 0 < start <= end <= len(source_lines):
        return None
    # Normalize caller lines once; retain exact line coordinates through masking.
    lines = [line.rstrip('\r\n') for line in source_lines]
    text = '\n'.join(lines)
    masked = code_mask(text)
    mask = ''.join(char if char in '\r\n' else replacement for char, replacement in zip(text, masked))
    key = (str(source_range.get('symbol') or ''), start, end)
    identities = lambda rows: {(str(row['symbol']), row['start_line'], row['end_line']) for row in rows}
    if key not in identities(property_callback_ranges(lines)) or key not in identities(property_callback_ranges(mask.splitlines())):
        return None
    header = PROPERTY_CALLBACK_RE.match(mask.splitlines()[start-1])
    if header is None or not re.match(r'\s*' + _NAME + r'\s*:', mask.splitlines()[start-1]):
        return None  # Class fields use '=', not object property ':'.
    offsets = [0]
    for line in lines[:-1]:
        offsets.append(offsets[-1] + len(line) + 1)
    location = offsets[start-1] + header.start(1)
    pairs = _pairs(mask)
    if pairs is None:
        return None
    parents = [opening for opening, closing in pairs.items() if mask[opening] == '{' and opening < location < closing]
    if not parents:
        return None
    opening = max(parents)
    closing = pairs[opening]
    if not _object_open(mask, opening, pairs):
        return None
    first, last = text.count('\n', 0, opening)+1, text.count('\n', 0, closing)+1
    if not first <= start <= end <= last or last-first+1 > max_lines:
        return None
    content = '\n'.join(lines[first-1:last])
    if len(content) > char_budget:
        return None
    scalar = False
    callback_found = False
    for left, right in _members(mask, opening, closing, pairs):
        masked_member = mask[left:right]
        member = text[left:right]
        match = re.match(r'\s*(' + _NAME + r')\s*:', masked_member)
        if match is None:
            return None  # No spreads, computed keys, getters or shorthand.
        value = member[match.end():].strip()
        if _SCALAR.fullmatch(value):
            scalar = True
            continue
        callback = PROPERTY_CALLBACK_RE.match(masked_member)
        if callback is None:
            return None  # Nested objects are not scalar sibling evidence.
        body_open = left + callback.end() - 1
        if body_open not in pairs or mask[pairs[body_open]+1:right].strip():
            return None
        if left <= location < right:
            callback_found = True
    if not scalar or not callback_found:
        return None
    return {**source_range, 'start_line': first, 'end_line': last,
            'selection_reason': 'callback_binding_context'}
