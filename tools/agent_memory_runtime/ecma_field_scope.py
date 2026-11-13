# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Filter existing field-map input, without introducing field entities."""
import re
from .ecma_callback_mask import callback_mask_lines


def direct_field_lines(lines, start, end):
    original = lines[start + 1:end]
    masked = callback_mask_lines(lines[start:end + 1])
    if masked is None:
        return original
    stack = []
    result = []
    pairs = {')': '(', ']': '[', '}': '{'}
    for index, line in enumerate(masked):
        if 0 < index < len(masked) - 1 and stack == ['{']:
            result.append(line)
        for char in line:
            if char in '([{':
                stack.append(char)
            elif char in ')]}':
                if not stack or stack.pop() != pairs[char]:
                    return original
    # Unsupported/unbalanced scope falls back as a whole, not an absence claim.
    return original if stack else result


def collect_field_types(lines, container, field_re):
    if not container:
        return {}
    result = {}
    for line in direct_field_lines(lines, container.start, container.end):
        match = field_re.match(line)
        if match and "(" not in line.split(":", 1)[0]:
            result[match.group(1)] = re.split(r"[<,?. ]", match.group(2).strip())[0]
    return result
