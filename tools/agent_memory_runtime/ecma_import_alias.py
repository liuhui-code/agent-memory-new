# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Conservative identity resolution for directly invoked named import aliases."""
import re
from .ecma_callback_mask import callback_mask_lines


def alias_target(alias, original, body, signature, local_names):
    # Alias resolution is not lexical scope certification. Ambiguous syntax or
    # any visible shadow makes this new binding unavailable, not a different callee.
    if not original:
        return None
    if alias in local_names or re.search(r'\b' + re.escape(alias) + r'\b', signature):
        return None
    masked = callback_mask_lines(body.splitlines())
    if masked is None:
        return None
    code = '\n'.join(masked).partition('{')[2]
    if '=>' in code or re.search(r'\b(?:function|class|catch)\b', code):
        return None
    if re.search(r'\.\s*' + re.escape(alias) + r'\s*\(', code):
        return None
    # No declaration parser: any local binding statement is outside this
    # narrow direct-call proof, including multiline/comma/destructured bindings.
    if re.search(r'\b(?:const|let|var)\b', code):
        return None
    if re.search(r'[:,{[]\s*' + re.escape(alias) + r'\s*[,}\]]', code):
        return None
    if re.search(r'\b' + re.escape(alias) + r'\s*=(?!=)', code):
        return None
    return original


def alias_bindings(imports):
    groups = {}
    for name, alias, path in imports:
        groups.setdefault(alias, []).append((name, path))
    return {alias: rows[0][0] if len(rows) == 1 else None
            for alias, rows in groups.items()
            if len(rows) != 1 or rows[0][0] != alias}
