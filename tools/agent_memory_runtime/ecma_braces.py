# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations


def block_end(lines: list[str], start: int) -> int:
    """Return the closing line for a block, ignoring literal and comment braces."""
    depth = 0
    opened = False
    state = {"quote": "", "block_comment": False}
    for index in range(start, len(lines)):
        opens, closes = structural_braces(lines[index], state)
        depth += opens - closes
        opened = opened or bool(opens)
        if opened and depth <= 0:
            return index
    return start


def structural_braces(line: str, state: dict[str, str | bool]) -> tuple[int, int]:
    """Count braces that are source structure rather than literal content."""
    opens = 0
    closes = 0
    index = 0
    while index < len(line):
        char = line[index]
        following = line[index + 1] if index + 1 < len(line) else ""
        quote = str(state["quote"])
        if state["block_comment"]:
            if char == "*" and following == "/":
                state["block_comment"] = False
                index += 2
                continue
            index += 1
            continue
        if quote:
            if char == "\\":
                index += 2
                continue
            if char == quote:
                state["quote"] = ""
            index += 1
            continue
        if char == "/" and following == "/":
            break
        if char == "/" and following == "*":
            state["block_comment"] = True
            index += 2
            continue
        if char in {"'", '"', "`"}:
            state["quote"] = char
            index += 1
            continue
        if char == "{":
            opens += 1
        elif char == "}":
            closes += 1
        index += 1
    return opens, closes
