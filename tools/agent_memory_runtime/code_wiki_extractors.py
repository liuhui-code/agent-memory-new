# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .arkts_behavior_markers import extract_arkts_behavior_markers
from .arkts_ui_behavior import extract_arkts_operation_names
from .models import CODE_EXTENSIONS, IGNORE_DIRS
from .text import identifier_tokens, unique_list


ARKTS_BUILDER_COMPONENTS = {
    "Blank", "Button", "Canvas", "Checkbox", "Column", "Divider", "Flex",
    "ForEach", "Grid", "GridItem", "Image", "List", "ListItem", "Navigation",
    "Navigator", "Progress", "Radio", "RelativeContainer", "Repeat", "Row",
    "Scroll", "Search", "Select", "Slider", "Stack", "Swiper", "Tabs", "Text",
    "TextArea", "TextInput", "Toggle", "Video", "WaterFlow",
}
COMPONENT_ALIAS_EXCLUDED_SUFFIXES = ("Page", "Screen")

def should_skip_dir(path: Path) -> bool:
    return any(part in IGNORE_DIRS for part in path.parts)



def language_for(path: Path) -> str | None:
    return CODE_EXTENSIONS.get(path.suffix.lower())



def summarize_file(path: Path, language: str) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if language == "Markdown":
        heading = next((line.lstrip("#").strip() for line in lines if line.startswith("#")), "")
        return heading or f"Markdown file with {len(lines)} non-empty lines"
    if language == "ArkTS":
        symbols = extract_symbols(path, language)
        components = [name for name, kind in symbols if kind == "component"]
        routes = [name for name, kind in symbols if kind == "route"]
        resources = [name for name, kind in symbols if kind == "resource"]
        operations = extract_arkts_operation_names(text)
        behavior = extract_arkts_behavior_markers(text)
        parts = [f"ArkTS file with {len(lines)} non-empty lines"]
        if components:
            parts.append("components: " + ", ".join(sorted(set(components))[:5]))
            alias_components = [
                name for name in components
                if not name.endswith(COMPONENT_ALIAS_EXCLUDED_SUFFIXES)
            ]
            aliases = unique_list(identifier_tokens(" ".join(alias_components)))
            if aliases:
                parts.append("component terms: " + ", ".join(aliases[:12]))
        if routes:
            parts.append("routes: " + ", ".join(sorted(set(routes))[:5]))
        if resources:
            parts.append("resources: " + ", ".join(sorted(set(resources))[:5]))
        if operations:
            parts.append("operations: " + ", ".join(operations))
        if behavior:
            parts.append("behavior: " + ", ".join(behavior))
        return "; ".join(parts)
    if language == "HarmonyOS Config":
        symbols = extract_symbols(path, language)
        grouped: dict[str, list[str]] = {}
        for name, kind in symbols:
            grouped.setdefault(kind, []).append(name)
        parts = [f"HarmonyOS config with {len(lines)} non-empty lines"]
        for kind in ("ability", "permission", "dependency", "page_profile"):
            names = grouped.get(kind, [])
            if names:
                parts.append(f"{kind}s: " + ", ".join(sorted(set(names))[:5]))
        return "; ".join(parts)
    return f"{language} file with {len(lines)} non-empty lines"



def summarize_symbol(file_path: str, symbol: str, symbol_type: str | None, language: str) -> str:
    kind = symbol_type or "symbol"
    if language == "ArkTS":
        if kind == "component":
            return f"ArkTS component {symbol} declared in {file_path}"
        if kind == "route":
            return f"ArkTS route target {symbol} referenced by {file_path}"
        if kind == "resource":
            return f"ArkTS resource {symbol} referenced by {file_path}"
        if kind == "function":
            return f"ArkTS function or lifecycle method {symbol} in {file_path}"
        if kind == "class":
            return f"ArkTS class {symbol} declared in {file_path}"
    if language == "HarmonyOS Config":
        return f"HarmonyOS {kind} {symbol} configured in {file_path}"
    return f"{kind} {symbol} in {file_path}"



def extract_symbols(path: Path, language: str) -> list[tuple[str, str]]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    symbols: list[tuple[str, str]] = []
    patterns: list[tuple[str, str]]
    if language == "Python":
        patterns = [(r"^\s*def\s+([A-Za-z_]\w*)\s*\(", "function"), (r"^\s*class\s+([A-Za-z_]\w*)", "class")]
    elif language in {"TypeScript", "JavaScript"}:
        patterns = [
            (r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(", "function"),
            (r"^\s*(?:export\s+)?class\s+([A-Za-z_$][\w$]*)", "class"),
            (r"^\s*(?:export\s+)?interface\s+([A-Za-z_$][\w$]*)", "interface"),
            (r"^\s*const\s+([A-Za-z_$][\w$]*)\s*=", "const"),
            (r"^\s*(?:(?:private|public|protected|override|async|static)\s+)*([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*(?::\s*[^ {]+)?\s*\{", "function"),
        ]
    elif language == "ArkTS":
        patterns = [
            (r"^\s*(?:export\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(", "function"),
            (r"^\s*(?:export\s+)?class\s+([A-Za-z_$][\w$]*)", "class"),
            (r"^\s*(?:export\s+)?interface\s+([A-Za-z_$][\w$]*)", "interface"),
            (r"^\s*(?:export\s+)?struct\s+([A-Za-z_$][\w$]*)", "component"),
            (r"^\s*(?:(?:private|public|protected|override|async|static)\s+)*([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*(?::\s*[^ {]+)?\s*\{", "function"),
        ]
    elif language == "Dart":
        patterns = [
            (r"^\s*class\s+([A-Za-z_]\w*)", "class"),
            (r"^\s*(?:Future<[^>]+>|void|Widget)\s+([A-Za-z_]\w*)\s*\(", "function"),
        ]
    elif language == "Swift":
        patterns = [
            (r"^\s*class\s+([A-Za-z_]\w*)", "class"),
            (r"^\s*struct\s+([A-Za-z_]\w*)", "struct"),
            (r"^\s*func\s+([A-Za-z_]\w*)\s*\(", "function"),
        ]
    elif language == "Markdown":
        patterns = [(r"^(#{1,6})\s+(.+)$", "heading")]
    elif language == "HarmonyOS Config":
        return extract_harmonyos_config_symbols(text)
    else:
        patterns = []
    for line in text.splitlines():
        for pattern, kind in patterns:
            match = re.search(pattern, line)
            if match:
                if language == "Markdown":
                    name = match.group(2).strip()
                else:
                    name = match.group(1).strip()
                if name in {"if", "for", "while", "switch", "catch"}:
                    continue
                if language == "ArkTS" and kind == "function" and name in ARKTS_BUILDER_COMPONENTS:
                    continue
                symbols.append((name, kind))
    if language == "ArkTS":
        symbols.extend(extract_arkts_reference_symbols(text))
    return symbols



def extract_arkts_reference_symbols(text: str) -> list[tuple[str, str]]:
    symbols: list[tuple[str, str]] = []
    for match in re.finditer(r"@(State|Prop|Link|Provide|Consume|ObjectLink|Local|Param)\s+([A-Za-z_][A-Za-z0-9_]*)", text):
        symbols.append((match.group(2), "state"))
    for match in re.finditer(r"@Event\s+([A-Za-z_][A-Za-z0-9_]*)", text):
        symbols.append((match.group(1), "event"))
    for match in re.finditer(
        r"\brouter\.(?:pushUrl|replaceUrl)\s*\(\s*\{[^}]*\burl\s*:\s*['\"]([^'\"]+)['\"]",
        text,
        re.DOTALL,
    ):
        symbols.append((match.group(1), "route"))
    for match in re.finditer(
        r"\.(?:pushPath|replacePath)\s*\(\s*\{[^}]*\bname\s*:\s*['\"]([^'\"]+)['\"]",
        text,
        re.DOTALL,
    ):
        symbols.append((match.group(1), "route"))
    for match in re.finditer(r"\$r\s*\(\s*['\"]([^'\"]+)['\"]", text):
        symbols.append((match.group(1), "resource"))
    return symbols



def extract_harmonyos_config_symbols(text: str) -> list[tuple[str, str]]:
    symbols: list[tuple[str, str]] = []
    for match in re.finditer(r'"name"\s*:\s*"([^"]+)"', text):
        name = match.group(1)
        if "permission." in name:
            symbols.append((name, "permission"))
        elif name.endswith("Ability"):
            symbols.append((name, "ability"))
    for block_name in ("dependencies", "devDependencies", "overrides"):
        block_match = re.search(rf'"{block_name}"\s*:\s*\{{(.*?)\}}', text, re.DOTALL)
        if not block_match:
            continue
        for dep in re.finditer(r'"([^"]+)"\s*:', block_match.group(1)):
            symbols.append((dep.group(1), "dependency"))
    for match in re.finditer(r'"pages"\s*:\s*"([^"]+)"', text):
        symbols.append((match.group(1), "page_profile"))
    return symbols



def extract_log_statements(path: Path, language: str) -> list[dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    logs: list[dict[str, Any]] = []
    current_function: str | None = None
    current_indent = -1
    for line_number, line in enumerate(text.splitlines(), start=1):
        symbol = function_symbol_on_line(line, language)
        if symbol:
            current_function, current_indent = symbol
        elif language == "Python" and current_function:
            stripped = line.strip()
            indent = len(line) - len(line.lstrip())
            if stripped and indent <= current_indent and not stripped.startswith(("#", "@")):
                current_function = None
                current_indent = -1
        log = log_statement_on_line(line, language)
        if not log:
            continue
        log["line"] = line_number
        log["function"] = current_function
        log["raw_statement"] = line.strip()
        logs.append(log)
    return logs



def function_symbol_on_line(line: str, language: str) -> tuple[str, int] | None:
    indent = len(line) - len(line.lstrip())
    if language == "Python":
        match = re.match(r"^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)\s*\(", line)
        return (match.group(1), indent) if match else None
    if language in {"TypeScript", "JavaScript"}:
        patterns = [
            r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(",
            r"^\s*(?:export\s+)?const\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\(",
            r"^\s*(?:export\s+)?class\s+([A-Za-z_$][\w$]*)",
            r"^\s*(?:(?:private|public|protected|override|async|static)\s+)*([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*(?::\s*[^ {]+)?\s*\{",
        ]
    elif language == "ArkTS":
        patterns = [
            r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(",
            r"^\s*(?:export\s+)?class\s+([A-Za-z_$][\w$]*)",
            r"^\s*(?:export\s+)?struct\s+([A-Za-z_$][\w$]*)",
            r"^\s*(?:(?:private|public|protected|override|async|static)\s+)*([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*(?::\s*[^ {]+)?\s*\{",
        ]
    elif language == "Dart":
        patterns = [
            r"^\s*(?:Future<[^>]+>|void|Widget|String|int|bool|double)\s+([A-Za-z_]\w*)\s*\(",
            r"^\s*class\s+([A-Za-z_]\w*)",
        ]
    elif language == "Swift":
        patterns = [
            r"^\s*func\s+([A-Za-z_]\w*)\s*\(",
            r"^\s*(?:class|struct)\s+([A-Za-z_]\w*)",
        ]
    else:
        patterns = []
    for pattern in patterns:
        match = re.match(pattern, line)
        if match:
            name = match.group(1)
            if name in {"if", "for", "while", "switch", "catch"}:
                continue
            return name, indent
    return None



def log_statement_on_line(line: str, language: str) -> dict[str, Any] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith(("#", "//")):
        return None
    patterns: list[tuple[str, str, str]]
    if language == "Python":
        patterns = [
            (r"\bprint\s*\((.*)\)", "print", "print"),
            (r"\b(logging|logger)\.(debug|info|warning|warn|error|exception)\s*\((.*)\)", "", ""),
        ]
    elif language in {"TypeScript", "JavaScript"}:
        patterns = [
            (r"\bconsole\.(log|info|warn|error|debug)\s*\((.*)\)", "console", ""),
            (r"\blogger\.(log|info|warn|error|debug)\s*\((.*)\)", "logger", ""),
        ]
    elif language == "ArkTS":
        patterns = [
            (r"\bconsole\.(log|info|warn|error|debug)\s*\((.*)\)", "console", ""),
            (r"\blogger\.(log|info|warn|error|debug)\s*\((.*)\)", "logger", ""),
            (r"\bhilog\.(debug|info|warn|error|fatal)\s*\((.*)\)", "hilog", ""),
        ]
    elif language == "Dart":
        patterns = [
            (r"\bprint\s*\((.*)\)", "print", "print"),
            (r"\bdebugPrint\s*\((.*)\)", "debugPrint", "debug"),
            (r"\blog\s*\((.*)\)", "log", "log"),
        ]
    elif language == "Swift":
        patterns = [
            (r"\bprint\s*\((.*)\)", "print", "print"),
            (r"\bNSLog\s*\((.*)\)", "NSLog", "log"),
            (r"\bos_log\s*\((.*)\)", "os_log", "log"),
            (r"\blogger\.(debug|info|warning|error)\s*\((.*)\)", "logger", ""),
        ]
    else:
        return None
    for pattern, logger_name, fixed_level in patterns:
        match = re.search(pattern, stripped)
        if not match:
            continue
        if language == "Python" and logger_name == "":
            logger = match.group(1)
            level = match.group(2)
            args_text = match.group(3)
        elif language in {"TypeScript", "JavaScript", "ArkTS"}:
            logger = logger_name
            level = match.group(1)
            args_text = match.group(2)
        elif language == "Swift" and logger_name == "logger":
            logger = logger_name
            level = match.group(1)
            args_text = match.group(2)
        else:
            logger = logger_name
            level = fixed_level
            args_text = match.group(1)
        return {
            "level": "warning" if level == "warn" else level,
            "logger": logger,
            "message_template": message_template_for_args(logger, args_text),
        }
    return None



def message_template_for_args(logger: str, args_text: str) -> str:
    literals = string_literals(args_text)
    if logger == "hilog" and len(literals) >= 2:
        return literals[1]
    if literals:
        return literals[0]
    return args_text.strip()



def string_literals(text: str) -> list[str]:
    return [match.group(2) for match in re.finditer(r"""(['"])(.*?)(?<!\\)\1""", text)]
