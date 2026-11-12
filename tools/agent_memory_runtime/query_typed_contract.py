# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

"""Conservative explicit type-relation evidence; never infer a data-flow contract."""
from __future__ import annotations

import re
from typing import Any

_IDENTIFIER = r"[A-Za-z_$][A-Za-z0-9_$]*"
_DISTINCTIVE = re.compile(r"\b[A-Z][a-z0-9]+(?:[A-Z][A-Za-z0-9]*)+\b")
_TOKEN = re.compile(_IDENTIFIER)
_TYPE_KINDS = {"interface", "class", "enum", "struct", "object", "component"}


def classify_contract(query: str) -> dict[str, Any] | None:
    """Recognize one explicitly named relation, otherwise leave normal retrieval alone."""
    if re.search(r"\b(?:not|no|except|excluding|avoid)\b|rather than", query, re.IGNORECASE):
        return None
    names = set(_DISTINCTIVE.findall(query))
    if len(names) != 1:
        return None
    identifier = next(iter(names))
    escaped = re.escape(identifier)
    if re.search(r"[/\\.]" + escaped + r"|" + escaped + r"(?:[<\[|]|\.[A-Za-z_]|/)", query):
        return None
    literal = bool(re.search(r"\b(?:string\s+literal|literal\s+string)\s+[`'\"]?" + escaped + r"\b", query))
    declaration = bool(re.search(r"\b" + escaped + r"\s+(?:interface|class|type)\s+declaration\b", query))
    declaration |= bool(re.search(r"\b(?:interface|class|type)\s+declaration\s+(?:of\s+)?" + escaped + r"\b", query))
    parameter = bool(re.search(r"\b" + escaped + r"\s+parameters?\b", query))
    parameter |= bool(re.search(r"\bparameters?\s+(?:of\s+)?type\s+" + escaped + r"\b", query))
    parameter |= bool(re.search(r"\baccepts?\s+" + escaped + r"\b", query))
    returns = bool(re.search(r"\breturns?\s+" + escaped + r"\b", query))
    returns |= bool(re.search(r"\breturn\s+type\s+(?:is\s+)?" + escaped + r"\b", query))
    kinds = [kind for kind, active in [("literal", literal), ("declaration", declaration), ("parameter", parameter), ("return", returns)] if active]
    if len(kinds) != 1:
        return None
    result: dict[str, Any] = {"kind": kinds[0], "identifier": identifier}
    if result["kind"] == "parameter":
        if re.search(r"\b(?:without\s+using|unused)\b", query):
            result["unused"] = True
        operation = re.search(r"\binvokes?\s+(" + _IDENTIFIER + r")\s+on\s+(?:that|the)\s+parameter\b", query)
        if operation:
            result["operation"] = operation.group(1)
    return result


def _split(text: str) -> list[str] | None:
    """Split parameters without treating nested generic commas as boundaries."""
    stack: list[str] = []
    pairs = {">": "<", "]": "[", "}": "{"}
    result: list[str] = []
    start = 0
    for index, char in enumerate(text):
        if char in "<[{":
            stack.append(char)
        elif char in ">]}":
            if not stack or stack.pop() != pairs[char]:
                return None
        elif char in "()":
            return None  # Callback signatures need a real language parser.
        elif char == "," and not stack:
            result.append(text[start:index].strip())
            start = index + 1
    if stack:
        return None
    result.append(text[start:].strip())
    return result


def _signature(item: dict[str, Any]) -> tuple[list[tuple[str, str]], str] | None:
    signature = str(item.get("signature") or "").strip()
    if any(marker in signature for marker in ["'", '"', "`", "//", "/*", "*/", "\n", "="]):
        return None
    match = re.fullmatch(r"(" + _IDENTIFIER + r")\s*\((.*)\)\s*:\s*(.+)", signature)
    if not match or match.group(1) != str(item.get("symbol") or ""):
        return None
    parts = _split(match.group(2))
    if parts is None:
        return None
    parameters: list[tuple[str, str]] = []
    for part in parts:
        if not part:
            continue
        parameter = re.fullmatch(r"(" + _IDENTIFIER + r")\??\s*:\s*(.+)", part)
        if not parameter:
            return None
        parameters.append((parameter.group(1), parameter.group(2).strip()))
    return parameters, match.group(3).strip()


def match_candidate(item: dict[str, Any], descriptor: dict[str, Any] | None) -> bool:
    """Test evidence identity, not semantic correctness or runtime receiver flow."""
    if not isinstance(descriptor, dict):
        return False
    name = descriptor.get("identifier")
    if not isinstance(name, str) or not _DISTINCTIVE.fullmatch(name):
        return False
    kind = descriptor.get("kind")
    symbol_type = str(item.get("symbol_type") or "")
    if kind == "declaration":
        return symbol_type in _TYPE_KINDS and item.get("symbol") == name
    if symbol_type not in {"function", "method"}:
        return False
    if kind == "literal":
        return name.casefold() in _TOKEN.findall(str(item.get("string_evidence") or "").casefold())
    signature = _signature(item)
    if signature is None:
        return False
    parameters, returns = signature
    if kind == "return":
        return returns == name
    if kind != "parameter" or descriptor.get("unused"):
        # Absence in bounded lexical method evidence cannot certify non-use.
        return False
    names = [parameter for parameter, type_name in parameters if type_name == name]
    if len(names) != 1:
        return False
    operation = descriptor.get("operation")
    if operation:
        tokens = set(_TOKEN.findall(str(item.get("method_evidence") or "").casefold()))
        return names[0].casefold() in tokens and str(operation).casefold() in tokens
    return True
