# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .ecma_callable_headers import CallableHeader

from .ecma_braces import block_end


SIGNATURE_TOKENS = re.compile(
    r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|'
    r'`(?:\\.|[^`\\])*`|=>|[A-Za-z_$][\w$]*|[^\s]', re.DOTALL,
)


def signature_terminator(tail: str, *, arrow: bool = False) -> int | None:
    """Find a body brace/arrow beyond return-type structure and comments."""
    stack: list[tuple[str, int]] = []
    function_type_parameters = False
    typed = False
    expects_type = False
    previous_end = 0
    for match in SIGNATURE_TOKENS.finditer(tail):
        token = match.group()
        if token.startswith(('//', '/*')):
            continue
        gap = tail[previous_end:match.start()]
        previous_end = match.end()
        if not stack:
            if token in {')', ']', '}'}:
                return None
            if typed and not expects_type and "\n" in gap:
                if re.match(r"[A-Za-z_$]", token) and token not in {'extends', 'is'}:
                    return None
            if token == ':' and not typed:
                typed = expects_type = True
                continue
            if token == ';':
                return None
            if arrow and token == '=>' and not function_type_parameters:
                return match.start()
            if token == '{' and not arrow and (not typed or not expects_type):
                return match.start()
            if not typed:
                return None
        if token in ('(', '[', '<', '{'):
            stack.append(({'(': ')', '[': ']', '<': '>', '{': '}'}[token], match.end()))
        elif stack and token == stack[-1][0]:
            _, opening = stack.pop()
            inner = without_comments(tail[opening:match.start()]).strip()
            function_type_parameters = not stack and token == ')' and (
                not inner or bool(re.match(r"(?:\.\.\.)?[\w$]+\s*[?:,]", inner))
            )
            expects_type = False
        elif not stack:
            function_type_parameters = False
            expects_type = token in {'|', '&', '?', ':', '.', '=>', 'keyof', 'typeof',
                                     'readonly', 'infer', 'is', 'extends'}
    return None


def source_position(text: str, start: int, offset: int) -> tuple[int, int]:
    prefix = text[:offset]
    return start + prefix.count('\n'), len(prefix.rsplit('\n', 1)[-1])


def callable_block_end(lines: list[str], start: int, header: CallableHeader) -> int:
    """Count from the proven body opening, never a brace in its signature."""
    if header.body_start is None:
        return header.header_end if header.header_end is not None else start
    line, column = header.body_start
    if not (0 <= line < len(lines) and 0 <= column < len(lines[line])):
        return start
    if lines[line][column] == "{":
        return block_end(lines, line, column)
    return expression_end(lines, line, column)


def without_comments(value: str) -> str:
    return SIGNATURE_TOKENS.sub(
        lambda match: " " if match.group().startswith(("//", "/*")) else match.group(),
        value,
    )


def expression_start(value: str) -> int | None:
    return next((match.start() for match in SIGNATURE_TOKENS.finditer(value)
                 if not match.group().startswith(("//", "/*"))), None)


def expression_end(lines: list[str], start: int, column: int) -> int:
    """Keep balanced multiline arrow expressions without claiming the next block."""
    stack: list[str] = []
    quote = ""
    comment = False
    last = ""
    for line_index in range(start, len(lines)):
        line = lines[line_index]
        index = column if line_index == start else 0
        while index < len(line):
            char = line[index]
            following = line[index + 1] if index + 1 < len(line) else ""
            if comment:
                if char == "*" and following == "/":
                    comment = False
                    index += 2
                    continue
            elif quote:
                if char == "\\":
                    index += 2
                    continue
                if char == quote:
                    quote = ""
            elif char == "/" and following == "/":
                break
            elif char == "/" and following == "*":
                comment = True
                index += 2
                continue
            elif char in {"'", '"', "`"}:
                quote = char
                last = "literal"
            elif char in "([{":
                stack.append({"(": ")", "[": "]", "{": "}"}[char])
                last = char
            elif char in ")]}":
                if not stack:
                    return max(start, line_index - 1)
                if char != stack.pop():
                    return start
                last = char
            elif char in ";," and not stack:
                return line_index
            elif not char.isspace():
                last = char
            index += 1
        if not (stack or quote or comment):
            next_line = lines[line_index + 1].lstrip() if line_index + 1 < len(lines) else ""
            if last in {".", "?", ":", "=", "+", "-", "*", "/", "%", "&", "|", "^", "<", ">"}:
                continue
            if next_line.startswith((".", "?.", "? ", ": ", "&&", "||", "??")):
                continue
            return line_index
    return start
