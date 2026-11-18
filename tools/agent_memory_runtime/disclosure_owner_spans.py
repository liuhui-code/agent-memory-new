# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Finite top-level declared-owner partitions, not a receiver-flow certificate."""
import re

DECLARATION = re.compile(
    r'\b(?:class|struct)\s+[A-Za-z_$][\w$]*'
    r'(?:\s+implements\s+[A-Za-z_$][\w$]*(?:\s*,\s*[A-Za-z_$][\w$]*)*)?\s*\{'
)
KEYWORD = re.compile(r'\b(?:class|struct)\b')


def declared_owner_spans(masked):
    """None means preserve legacy. Nested/unsupported declarations are unknown."""
    if len(masked) > 65536:
        return None
    headers = list(DECLARATION.finditer(masked))
    if not headers or len(headers) != len(list(KEYWORD.finditer(masked))):
        return None
    starts = {m.end()-1: m.start() for m in headers}
    stack = []
    spans = []
    for index, char in enumerate(masked):
        if char == '{':
            if index in starts and stack:
                return None
            stack.append(index)
        elif char == '}':
            if not stack:
                return None
            start = stack.pop()
            if start in starts:
                spans.append((starts[start], index+1))
    if stack or len(spans) != len(headers):
        return None
    return spans
