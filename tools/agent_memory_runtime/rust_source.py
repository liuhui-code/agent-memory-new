# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

"""Source-only Rust declaration navigation; not a compiler or call resolver."""

from __future__ import annotations

import bisect
import re
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path


MAX_SOURCE_CHARS = 1_000_000
MAX_DECLARATIONS = 2000
MAX_HEADER_TOKENS = 512
MAX_SCOPE_DEPTH = 32
LIMITATION = "Rust source-only declarations; macros/cfg/types/calls unresolved"
TOKEN = re.compile(r"r#[A-Za-z_]\w*|[A-Za-z_]\w*|->|::|[^\s]")
IDENTIFIER = re.compile(r"(?:r#)?[A-Za-z_]\w*\Z")
RAW_STRING = re.compile(r'(?:br|cr|r)(#{0,255})"')
CHARACTER = re.compile(r"'(?:\\(?:u\{[0-9a-fA-F_]+\}|x[0-9a-fA-F]{2}|[^\n])|[^'\\\n])'")


def read_rust_text(path: Path) -> str:
    try:
        return path.read_bytes().decode("utf-8")
    except (OSError, UnicodeError):
        return ""


@dataclass(frozen=True)
class RustDeclaration:
    name: str
    qualified_name: str
    kind: str
    signature: str
    start_line: int
    end_line: int
    owner_name: str = ""


def masked_source(text: str) -> str:
    """Blank comments/literals without moving character or newline positions."""
    chars = list(text)
    position = 0
    while position < len(text):
        end = position
        if text.startswith("//", position):
            end = text.find("\n", position)
            end = len(text) if end < 0 else end
        elif text.startswith("/*", position):
            end, depth = position + 2, 1
            while end < len(text) and depth:
                if text.startswith("/*", end):
                    depth += 1
                    end += 2
                elif text.startswith("*/", end):
                    depth -= 1
                    end += 2
                else:
                    end += 1
        else:
            raw = RAW_STRING.match(text, position)
            if raw and (position == 0 or not (text[position - 1].isalnum() or text[position - 1] == "_")):
                terminator = '"' + raw.group(1)
                closing = text.find(terminator, raw.end())
                end = len(text) if closing < 0 else closing + len(terminator)
            elif text[position] == '"':
                end = position + 1
                while end < len(text):
                    if text[end] == "\\":
                        end = min(end + 2, len(text))
                    elif text[end] == '"':
                        end += 1
                        break
                    else:
                        end += 1
            elif text[position] == "'":
                character = CHARACTER.match(text, position)
                if character:
                    end = character.end()
        if end > position:
            for index in range(position, end):
                if chars[index] not in "\r\n":
                    chars[index] = " "
            position = end
        else:
            position += 1
    return "".join(chars)


def delimiter_pairs(tokens: list[re.Match[str]]) -> dict[int, int] | None:
    stack: list[tuple[str, int]] = []
    pairs: dict[int, int] = {}
    for index, token in enumerate(tokens):
        value = token.group()
        if value in {"(", "[", "{"}:
            stack.append((value, index))
        elif value in {")", "]", "}"}:
            expected = {")": "(", "]": "[", "}": "{"}[value]
            if not stack or stack[-1][0] != expected:
                return None
            _opening, start = stack.pop()
            pairs[start] = index
    return None if stack else pairs


def rust_declarations(text: str) -> list[RustDeclaration]:
    if len(text) > MAX_SOURCE_CHARS:
        return []
    masked = masked_source(text)
    tokens = list(TOKEN.finditer(masked))
    pairs = delimiter_pairs(tokens)
    if pairs is None:
        return []
    parser = DeclarationReader(text, masked, tokens, pairs)
    parser.walk(0, len(tokens), "", "")
    counts = Counter(item.qualified_name for item in parser.declarations)
    occurrences: Counter[str] = Counter()
    declarations = []
    for item in parser.declarations:
        occurrences[item.qualified_name] += 1
        if counts[item.qualified_name] > 1:
            item = replace(item, name=f"{item.qualified_name}@{item.start_line}:{occurrences[item.qualified_name]}")
        declarations.append(item)
    return declarations


class DeclarationReader:
    def __init__(self, text: str, masked: str, tokens: list[re.Match[str]], pairs: dict[int, int]) -> None:
        self.text, self.masked, self.tokens, self.pairs = text, masked, tokens, pairs
        self.newlines = [index for index, char in enumerate(text) if char == "\n"]
        self.declarations: list[RustDeclaration] = []

    def value(self, index: int) -> str:
        return self.tokens[index].group() if index < len(self.tokens) else ""

    def line(self, position: int) -> int:
        return bisect.bisect_left(self.newlines, position) + 1

    def skip_item(self, start: int, end: int) -> int:
        index = start
        while index < end:
            value = self.value(index)
            if value == ";":
                return index + 1
            if index in self.pairs:
                closing = self.pairs[index]
                if value == "{":
                    return closing + 1
                index = closing + 1
            else:
                index += 1
        return end

    def header_end(self, start: int, end: int) -> int | None:
        index, angle_depth = start, 0
        while index < end and index - start < MAX_HEADER_TOKENS:
            value = self.value(index)
            if value == "<":
                angle_depth += 1
            elif value == ">":
                angle_depth = max(0, angle_depth - 1)
            elif value in {"{", ";"} and angle_depth == 0:
                return index
            if index in self.pairs:
                index = self.pairs[index] + 1
            else:
                index += 1
        return None

    def item_keyword(self, start: int, end: int) -> int:
        index = start
        if self.value(index) == "pub":
            index += 1
            if self.value(index) == "(" and index in self.pairs:
                index = self.pairs[index] + 1
        while index < end and self.value(index) in {"const", "async", "unsafe", "safe", "extern", "default"}:
            index += 1
        return index

    def after_generics(self, start: int, end: int) -> int:
        if self.value(start) != "<":
            return start
        index, depth = start, 0
        while index < end and index - start < MAX_HEADER_TOKENS:
            value = self.value(index)
            depth += int(value == "<") - int(value == ">")
            if depth == 0:
                return index + 1
            index = self.pairs[index] + 1 if index in self.pairs else index + 1
        return end

    def walk(self, start: int, end: int, scope: str, owner: str, depth: int = 0) -> None:
        if depth > MAX_SCOPE_DEPTH:
            return
        index = start
        while index < end and len(self.declarations) < MAX_DECLARATIONS:
            if self.value(index) == "#":
                bracket = index + (2 if self.value(index + 1) == "!" else 1)
                if self.value(bracket) == "[" and bracket in self.pairs:
                    index = self.pairs[bracket] + 1
                    continue
            if self.value(index) == ";":
                index += 1
                continue
            keyword_at = self.item_keyword(index, end)
            keyword = self.value(keyword_at)
            if keyword not in {"fn", "struct", "enum", "trait", "mod", "impl"}:
                index = self.skip_item(index, end)
                continue
            if keyword == "fn":
                parameters = self.after_generics(keyword_at + 2, end)
                if self.value(parameters) != "(":
                    index = self.skip_item(index, end)
                    continue
            boundary = self.header_end(keyword_at + 1, end)
            if boundary is None:
                index = self.skip_item(index, end)
                continue
            is_body = self.value(boundary) == "{"
            closing = self.pairs.get(boundary, boundary)
            if keyword == "impl":
                if is_body:
                    head_at = self.after_generics(keyword_at + 1, boundary)
                    head = self.masked[self.tokens[head_at].start():self.tokens[boundary].start()].strip() if head_at < boundary else ""
                    head = re.split(r"\bwhere\b", head, maxsplit=1)[0].strip()
                    head = " ".join(head.split())
                    if head:
                        self.walk(boundary + 1, closing, scope, head, depth + 1)
            else:
                name = self.value(keyword_at + 1)
                if IDENTIFIER.fullmatch(name):
                    qualified = "::".join(part for part in (scope, owner, name) if part)
                    kind = "method" if keyword == "fn" and owner else "function" if keyword == "fn" else keyword
                    self.declarations.append(RustDeclaration(
                        name=qualified, qualified_name=qualified, kind=kind,
                        signature=" ".join(self.text[self.tokens[index].start():self.tokens[boundary].start()].split()),
                        start_line=self.line(self.tokens[index].start()),
                        end_line=self.line(self.tokens[closing].end() - 1),
                        owner_name=owner,
                    ))
                    if is_body and keyword in {"mod", "trait"}:
                        self.walk(boundary + 1, closing,
                                  qualified if keyword == "mod" else scope,
                                  name if keyword == "trait" else "", depth + 1)
            index = closing + 1


def rust_summary(text: str) -> str:
    declarations = rust_declarations(text)
    names = ", ".join(item.name for item in declarations[:8])
    return LIMITATION + ("; declarations: " + names if names else "; file-level navigation only")
