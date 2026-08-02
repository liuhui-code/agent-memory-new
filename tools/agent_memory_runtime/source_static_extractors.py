# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .text import identifier_tokens, unique_list


MAX_SUMMARY_ITEMS = 12
MAX_NATIVE_HEADER_LINES = 24
CONTROL_NAMES = {"catch", "for", "if", "switch", "while"}
NATIVE_NAME_BEFORE_PAREN = re.compile(
    r"(?P<name>[A-Za-z_~][\w]*(?:::[A-Za-z_~][\w]*)*)\s*$"
)
NATIVE_SUFFIX = re.compile(
    r"(?:(?:const|override|final|mutable)\s*|"
    r"noexcept(?:\s*\([^)]*\))?\s*|[&]+\s*|->\s*[^;{}]+\s*)*"
)


def extended_summary(path: Path, language: str, text: str | None = None) -> str | None:
    if language not in {"C/C++", "Build Artifact"}:
        return None
    text = read_text(path) if text is None else text
    lines = [line for line in text.splitlines() if line.strip()]
    symbols = extended_symbols_from_text(text, language)
    names = unique_list([name for name, _kind in symbols])[:MAX_SUMMARY_ITEMS]
    literals = bounded_literals(text)
    parts = [f"{language} file with {len(lines)} non-empty lines"]
    if names:
        parts.append("symbols: " + ", ".join(names))
    if literals:
        parts.append("literal terms: " + ", ".join(literals))
    return "; ".join(parts)


def extended_symbols(
    path: Path, language: str, text: str | None = None,
) -> list[tuple[str, str]] | None:
    if language not in {"C/C++", "Build Artifact"}:
        return None
    return extended_symbols_from_text(read_text(path) if text is None else text, language)


def extended_symbols_from_text(text: str, language: str) -> list[tuple[str, str]]:
    if language == "C/C++":
        values: list[tuple[str, str]] = []
        for line in text.splitlines():
            type_match = re.match(r"^\s*(?:class|struct)\s+([A-Za-z_]\w*)", line)
            if type_match:
                values.append((type_match.group(1), "class"))
        values.extend(
            (str(item["symbol"]), "function")
            for item in native_callable_ranges(text)
        )
        return unique_pairs(values)
    return unique_pairs(build_symbols(text))


def native_callable_ranges(text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    ranges: list[dict[str, Any]] = []
    index = 0
    while index < len(lines):
        brace = lines[index].find("{")
        header = native_callable_header(lines, index, brace) if brace >= 0 else None
        if header is None:
            index += 1
            continue
        start, qualified, signature = header
        name = qualified.split("::")[-1]
        end = block_end(lines, index)
        ranges.append({
            "symbol": name,
            "qualified_name": qualified,
            "kind": "function",
            "start_line": start + 1,
            "end_line": end,
            "signature": signature[:240],
        })
        index = max(index + 1, end)
    return ranges


def native_callable_header(
    lines: list[str], brace_index: int, brace_column: int,
) -> tuple[int, str, str] | None:
    lower = max(0, brace_index - MAX_NATIVE_HEADER_LINES + 1)
    best: tuple[int, str, str] | None = None
    for start in range(brace_index, lower - 1, -1):
        if start < brace_index and has_header_boundary(lines[start]):
            break
        raw = "\n".join([
            *lines[start:brace_index],
            lines[brace_index][:brace_column + 1],
        ])
        header = normalize_native_header(raw)
        parsed = native_header_name(header)
        if parsed is not None:
            first_code = next(
                (offset for offset, line in enumerate(lines[start:brace_index + 1])
                 if strip_native_comments(line).strip()),
                0,
            )
            best = (start + first_code, parsed, header.rstrip("{").strip())
    return best


def native_header_name(header: str) -> str | None:
    if not header.endswith("{") or "#" in header or "=" in header:
        return None
    value = header[:-1].rstrip()
    for close in range(len(value) - 1, -1, -1):
        if value[close] != ")":
            continue
        opened = matching_open_paren(value, close)
        if opened is None or not NATIVE_SUFFIX.fullmatch(value[close + 1:]):
            continue
        match = NATIVE_NAME_BEFORE_PAREN.search(value[:opened])
        if match is None:
            continue
        qualified = match.group("name")
        if qualified.split("::")[-1] in CONTROL_NAMES:
            continue
        prefix = value[:match.start()].strip()
        if prefix.endswith(("return", "new", ",")):
            continue
        return qualified
    return None


def matching_open_paren(value: str, close: int) -> int | None:
    depth = 0
    for index in range(close, -1, -1):
        if value[index] == ")":
            depth += 1
        elif value[index] == "(":
            depth -= 1
            if depth == 0:
                return index
    return None


def normalize_native_header(value: str) -> str:
    without_blocks = re.sub(r"/\*.*?\*/", " ", value, flags=re.DOTALL)
    without_lines = "\n".join(strip_native_comments(line) for line in without_blocks.splitlines())
    return " ".join(without_lines.split())


def strip_native_comments(value: str) -> str:
    return value.split("//", 1)[0]


def has_header_boundary(value: str) -> bool:
    code = strip_native_comments(value)
    return any(marker in code for marker in (";", "{", "}"))


def build_target_ranges(text: str) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for index, line in enumerate(text.splitlines(), start=1):
        make = re.match(r"^([A-Za-z0-9_./%+-]+)\s*:(?!=)", line)
        shell = re.match(r"^\s*(?:function\s+)?([A-Za-z_]\w*)\s*\(\s*\)\s*\{", line)
        match = make or shell
        if match:
            values.append({
                "symbol": match.group(1),
                "qualified_name": match.group(1),
                "kind": "build_target",
                "start_line": index,
                "end_line": index,
                "signature": line.strip()[:240],
            })
    cmake_pattern = re.compile(
        r"\b(?:add_library|add_executable|project)\s*\(\s*([A-Za-z0-9_.+-]+)",
        re.IGNORECASE,
    )
    for match in cmake_pattern.finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        values.append({
            "symbol": match.group(1),
            "qualified_name": match.group(1),
            "kind": "build_target",
            "start_line": line,
            "end_line": line,
            "signature": build_signature(text, match.start()),
        })
    for index, line in enumerate(text.splitlines(), start=1):
        variable = re.match(
            r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*(?::|\?|\+)?=",
            line,
        )
        if variable:
            values.append({
                "symbol": variable.group(1),
                "qualified_name": variable.group(1),
                "kind": "build_variable",
                "start_line": index,
                "end_line": index,
                "signature": line.strip()[:240],
            })
    return list({(item["symbol"], item["start_line"]): item for item in values}.values())


def build_signature(text: str, start: int) -> str:
    line_end = text.find("\n", start)
    return text[start:line_end if line_end >= 0 else len(text)][:240]


def build_symbols(text: str) -> list[tuple[str, str]]:
    return [
        (str(item["symbol"]), str(item.get("kind") or "build_target"))
        for item in build_target_ranges(text)
    ]


def bounded_literals(text: str) -> list[str]:
    values: list[str] = []
    for _quote, literal in re.findall(r"(['\"])([^'\"\n]{2,96})\1", text):
        if any(character.isalpha() for character in literal):
            values.extend([literal.casefold(), *identifier_tokens(literal)])
    return unique_list([item for item in values if 2 < len(item) <= 96])[:MAX_SUMMARY_ITEMS]


def block_end(lines: list[str], start: int) -> int:
    depth = 0
    seen = False
    for index in range(start, min(len(lines), start + 500)):
        depth += lines[index].count("{") - lines[index].count("}")
        seen = seen or "{" in lines[index]
        if seen and depth <= 0:
            return index + 1
    return min(len(lines), start + 500)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def unique_pairs(values: list[tuple[str, str]]) -> list[tuple[str, str]]:
    return list(dict.fromkeys(values))
