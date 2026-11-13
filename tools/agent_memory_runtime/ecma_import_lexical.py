# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Lexical admission only; preserve original regex captures and unknown behavior."""
from .ecma_callback_mask import callback_mask_lines


def admitted_import_matches(text, patterns):
    lines = callback_mask_lines(text.split('\n'))
    masked = None if lines is None else '\n'.join(lines)
    result = []
    for pattern in patterns:
        admitted = []
        for match in pattern.finditer(text):
            keyword = match.start() + len(match.group()) - len(match.group().lstrip())
            if masked is None or masked[keyword:keyword + 6] == 'import':
                admitted.append(match)
        result.append(admitted)
    return result
