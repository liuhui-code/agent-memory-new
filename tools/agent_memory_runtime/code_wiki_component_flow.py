# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re
from dataclasses import dataclass


COMPONENT_CALL_RE = re.compile(r"\b([A-Z][A-Za-z0-9_$]*)\s*\(\s*\{")
IDENTIFIER_RE = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*")


@dataclass(frozen=True)
class ComponentPropertyBinding:
    component: str
    properties: tuple[str, ...]


def extract_component_property_bindings(text: str) -> list[ComponentPropertyBinding]:
    text = mask_comments(text)
    bindings: list[ComponentPropertyBinding] = []
    for match in COMPONENT_CALL_RE.finditer(text):
        open_brace = text.find("{", match.start(), match.end())
        close_brace = matching_delimiter(text, open_brace, "{", "}")
        if close_brace is None:
            continue
        properties = tuple(top_level_property_names(text[open_brace + 1:close_brace]))
        if properties:
            bindings.append(ComponentPropertyBinding(match.group(1), properties))
    return bindings


def mask_comments(text: str) -> str:
    result = list(text)
    quote = ""
    escaped = False
    index = 0
    while index < len(text):
        char = text[index]
        following = text[index + 1] if index + 1 < len(text) else ""
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
            index += 1
            continue
        if char in {"'", '"', "`"}:
            quote = char
            index += 1
            continue
        if char == "/" and following == "/":
            end = text.find("\n", index + 2)
            end = len(text) if end < 0 else end
            for position in range(index, end):
                result[position] = " "
            index = end
            continue
        if char == "/" and following == "*":
            end = text.find("*/", index + 2)
            end = len(text) if end < 0 else end + 2
            for position in range(index, end):
                if result[position] != "\n":
                    result[position] = " "
            index = end
            continue
        index += 1
    return "".join(result)


def top_level_property_names(value: str) -> list[str]:
    names: list[str] = []
    for field in split_top_level(value):
        match = IDENTIFIER_RE.match(field.lstrip())
        if not match:
            continue
        remainder = field.lstrip()[match.end():].lstrip()
        if remainder.startswith(":"):
            names.append(match.group(0))
    return list(dict.fromkeys(names))


def split_top_level(value: str) -> list[str]:
    fields: list[str] = []
    start = 0
    stack: list[str] = []
    quote = ""
    escaped = False
    pairs = {"(": ")", "[": "]", "{": "}"}
    for index, char in enumerate(value):
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
            continue
        if char in {"'", '"', "`"}:
            quote = char
        elif char in pairs:
            stack.append(pairs[char])
        elif stack and char == stack[-1]:
            stack.pop()
        elif char == "," and not stack:
            fields.append(value[start:index])
            start = index + 1
    fields.append(value[start:])
    return fields


def matching_delimiter(
    text: str,
    start: int,
    opening: str,
    closing: str,
) -> int | None:
    if start < 0 or start >= len(text) or text[start] != opening:
        return None
    depth = 0
    quote = ""
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
            continue
        if char in {"'", '"', "`"}:
            quote = char
        elif char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return index
    return None
