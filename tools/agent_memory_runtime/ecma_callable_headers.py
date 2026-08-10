# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from dataclasses import dataclass
import re


CONTROL_NAMES = {"if", "for", "while", "switch", "catch"}
MAX_HEADER_LINES = 12
MAX_HEADER_CHARS = 2_048
IDENTIFIER_RE = re.compile(r"[A-Za-z_$][\w$]*")
METHOD_PREFIX_RE = re.compile(
    r"^\s*(?P<modifiers>(?:(?:public|private|protected|override|static|async)\s+)*)"
    r"(?P<name>[A-Za-z_$][\w$]*)\s*\("
)
FUNCTION_PREFIX_RE = re.compile(
    r"^\s*(?P<export>export\s+)?(?P<default>default\s+)?"
    r"(?P<async>async\s+)?function\s+(?P<name>[A-Za-z_$][\w$]*)\s*\("
)
TOP_LEVEL_ARROW_PREFIX_RE = re.compile(
    r"^\s*(?P<export>export\s+)?(?:const|let|var)\s+"
    r"(?P<name>[A-Za-z_$][\w$]*)\b"
)


@dataclass(frozen=True)
class CallableHeader:
    name: str
    params: str
    return_type: str | None
    async_value: bool
    visibility: str | None = None
    override: bool = False
    exported: bool = False


def named_callable_header(lines: list[str], start: int) -> CallableHeader | None:
    return method_header(lines, start) or top_level_callable_header(lines, start)


def top_level_callable_header(lines: list[str], start: int) -> CallableHeader | None:
    return function_header(lines, start) or arrow_function_header(lines, start)


def method_header(lines: list[str], start: int) -> CallableHeader | None:
    if start < 0 or start >= len(lines):
        return None
    offset = callable_declaration_offset(lines[start])
    match = METHOD_PREFIX_RE.match(lines[start][offset:])
    if match is None or match.group("name") in CONTROL_NAMES:
        return None
    parts = set(str(match.group("modifiers") or "").split())
    completed = complete_header(lines, start, offset + match.end() - 1)
    if completed is None:
        return None
    params, return_type = completed
    visibility = next(
        (value for value in ("public", "private", "protected") if value in parts),
        None,
    )
    return CallableHeader(
        name=match.group("name"),
        params=params,
        return_type=return_type,
        async_value="async" in parts,
        visibility=visibility,
        override="override" in parts,
    )


def function_header(lines: list[str], start: int) -> CallableHeader | None:
    if start < 0 or start >= len(lines):
        return None
    offset = callable_declaration_offset(lines[start])
    match = FUNCTION_PREFIX_RE.match(lines[start][offset:])
    if match is None:
        return None
    completed = complete_header(lines, start, offset + match.end() - 1)
    if completed is None:
        return None
    params, return_type = completed
    return CallableHeader(
        name=match.group("name"),
        params=params,
        return_type=return_type,
        async_value=bool(match.group("async")),
        exported=bool(match.group("export")),
    )


def arrow_function_header(lines: list[str], start: int) -> CallableHeader | None:
    if start < 0 or start >= len(lines):
        return None
    match = TOP_LEVEL_ARROW_PREFIX_RE.match(lines[start])
    if match is None:
        return None
    opening = arrow_initializer_opening(lines, start, match.end())
    if opening is None:
        return None
    completed = complete_arrow_header(lines, start, opening)
    if completed is None:
        return None
    params, return_type = completed
    return CallableHeader(
        name=match.group("name"),
        params=params,
        return_type=return_type,
        async_value=arrow_initializer_is_async(lines, start, opening),
        exported=bool(match.group("export")),
    )


def callable_declaration_offset(line: str) -> int:
    index = len(line) - len(line.lstrip())
    if index >= len(line) or line[index] != "@":
        return 0
    while index < len(line) and line[index] == "@":
        name = IDENTIFIER_RE.match(line, index + 1)
        if name is None:
            return 0
        index = name.end()
        if index < len(line) and line[index] == "(":
            closing = closing_parenthesis(line, index)
            if closing is None:
                return 0
            index = closing + 1
        if index >= len(line) or not line[index].isspace():
            return 0
        while index < len(line) and line[index].isspace():
            index += 1
    return index


def complete_header(
    lines: list[str], start: int, opening_column: int,
) -> tuple[str, str | None] | None:
    header = lines[start]
    for index in range(start, min(len(lines), start + MAX_HEADER_LINES)):
        if index > start:
            header += "\n" + lines[index]
        if len(header) > MAX_HEADER_CHARS:
            return None
        closing = closing_parenthesis(header, opening_column)
        if closing is None:
            continue
        tail = header[closing + 1:]
        brace = tail.find("{")
        terminator = tail.find(";")
        if terminator >= 0 and (brace < 0 or terminator < brace):
            return None
        if brace < 0:
            continue
        params = normalize_space(header[opening_column + 1:closing])
        suffix = normalize_space(tail[:brace])
        if suffix and not suffix.startswith(":"):
            return None
        return_type = normalize_return_type(suffix)
        return params, return_type
    return None


def arrow_initializer_opening(lines: list[str], start: int, prefix_end: int) -> int | None:
    header = lines[start]
    for index in range(start, min(len(lines), start + MAX_HEADER_LINES)):
        if index > start:
            header += "\n" + lines[index]
        if len(header) > MAX_HEADER_CHARS:
            return None
        assignment = top_level_assignment_index(header, prefix_end)
        if assignment is None:
            continue
        initializer = re.match(r"\s*(?:async\s+)?\(", header[assignment + 1:])
        if initializer is None:
            return None
        return assignment + initializer.end()
    return None


def arrow_initializer_is_async(lines: list[str], start: int, opening: int) -> bool:
    header = "\n".join(lines[start:min(len(lines), start + MAX_HEADER_LINES)])
    prefix = header[:opening]
    return bool(re.search(r"=\s*async\s*$", prefix))


def top_level_assignment_index(value: str, start: int) -> int | None:
    parens = brackets = braces = 0
    quote = ""
    for index in range(start, len(value)):
        char = value[index]
        previous = value[index - 1] if index else ""
        following = value[index + 1] if index + 1 < len(value) else ""
        if quote:
            if char == "\\":
                continue
            if char == quote:
                quote = ""
            continue
        if char in {"'", '"', "`"}:
            quote = char
        elif char == "(":
            parens += 1
        elif char == ")":
            parens -= 1
        elif char == "[":
            brackets += 1
        elif char == "]":
            brackets -= 1
        elif char == "{":
            braces += 1
        elif char == "}":
            braces -= 1
        elif char == "=" and not (parens or brackets or braces):
            if previous not in "!<=>" and following not in "=>":
                return index
    return None


def complete_arrow_header(
    lines: list[str], start: int, opening_column: int,
) -> tuple[str, str | None] | None:
    header = lines[start]
    for index in range(start, min(len(lines), start + MAX_HEADER_LINES)):
        if index > start:
            header += "\n" + lines[index]
        if len(header) > MAX_HEADER_CHARS:
            return None
        closing = closing_parenthesis(header, opening_column)
        if closing is None:
            continue
        tail = header[closing + 1:]
        arrow = tail.find("=>")
        if arrow < 0:
            continue
        suffix = normalize_space(tail[:arrow])
        if suffix and not suffix.startswith(":"):
            return None
        expression = tail[arrow + 2:].strip()
        if not expression:
            continue
        params = normalize_space(header[opening_column + 1:closing])
        return params, normalize_return_type(suffix)
    return None


def closing_parenthesis(value: str, opening: int) -> int | None:
    depth = 0
    quote = ""
    index = opening
    while index < len(value):
        char = value[index]
        if quote:
            if char == "\\":
                index += 2
                continue
            if char == quote:
                quote = ""
        elif char in {"'", '"', "`"}:
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return None


def normalize_return_type(value: str) -> str | None:
    text = normalize_space(value)
    return text[1:].strip() or None if text.startswith(":") else None


def normalize_space(value: str) -> str:
    return " ".join(value.split())
