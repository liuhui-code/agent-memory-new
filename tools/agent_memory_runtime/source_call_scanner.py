# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re


def scan_calls(text: str, pattern: str) -> list[tuple[int, str]]:
    """Return balanced calls found in code, excluding strings and comments."""
    if not pattern:
        return []
    return scan_calls_masked(text, code_mask(text), pattern)


def scan_calls_masked(text: str, mask: str, pattern: str) -> list[tuple[int, str]]:
    calls: list[tuple[int, str]] = []
    for match in re.finditer(pattern, mask):
        end = balanced_call_end(mask, match.end() - 1)
        if end is not None:
            calls.append((text.count("\n", 0, match.start()) + 1, text[match.start():end]))
    return calls


def balanced_call_end(mask: str, opening: int) -> int | None:
    depth = 0
    for index in range(opening, len(mask)):
        if mask[index] == "(":
            depth += 1
        elif mask[index] == ")":
            depth -= 1
            if depth == 0:
                return index + 1
    return None


def call_argument_count(call: str) -> int | None:
    mask = code_mask(call)
    opening = mask.find("(")
    if opening < 0 or balanced_call_end(mask, opening) is None:
        return None
    body = mask[opening + 1:-1]
    if not call[opening + 1:-1].strip():
        return 0
    depth = 0
    count = 1
    for char in body:
        if char in "([{":
            depth += 1
        elif char in ")]}" and depth:
            depth -= 1
        elif char == "," and depth == 0:
            count += 1
    return count


def code_mask(text: str) -> str:
    chars = list(text)
    state = "code"
    quote = ""
    index = 0
    while index < len(text):
        char = text[index]
        following = text[index + 1] if index + 1 < len(text) else ""
        if state == "line_comment":
            if char == "\n":
                state = "code"
            else:
                chars[index] = " "
        elif state == "block_comment":
            chars[index] = " "
            if char == "*" and following == "/":
                chars[index + 1] = " "
                state = "code"
                index += 1
        elif state == "string":
            if char != "\n":
                chars[index] = " "
            if char == "\\":
                if index + 1 < len(text) and text[index + 1] != "\n":
                    chars[index + 1] = " "
                index += 1
            elif char == quote:
                state = "code"
        elif char == "/" and following == "/":
            chars[index] = chars[index + 1] = " "
            state = "line_comment"
            index += 1
        elif char == "/" and following == "*":
            chars[index] = chars[index + 1] = " "
            state = "block_comment"
            index += 1
        elif char in {"'", '"', "`"}:
            chars[index] = " "
            quote = char
            state = "string"
        index += 1
    return "".join(chars)
