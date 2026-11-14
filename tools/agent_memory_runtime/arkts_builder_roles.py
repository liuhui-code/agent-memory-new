# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Positive supported ArkTS declaration fact, never an absence/operation proof."""
from collections import Counter
import re
from pathlib import Path
from .ecma_callback_mask import callback_mask_lines
from .ecma_callable_headers import method_header, top_level_callable_header


def attach_builder_roles(lines, language, file_path, containers, callables):
    if language != 'ArkTS' or Path(file_path).suffix != '.ets':
        return
    masked = callback_mask_lines(lines)
    if masked is None:
        return
    # No framework/import resolution: a bare Builder identifier may shadow it.
    without_decorators = re.sub(r'@Builder\b', '', '\n'.join(masked))
    if re.search(r'(?<![\w$])Builder(?![\w$])', without_decorators):
        return
    names = Counter(block.entity.qualified_name for block in callables)
    owners = Counter(container.name for container in containers)
    # One scan records exact nesting; no per-method whole-file lexical masking.
    scopes, stack = [], []
    for index, line in enumerate(masked):
        scopes.append(tuple(stack))
        for char in line:
            if char in '({[':
                stack.append((char, index))
            elif char in ')}]':
                if not stack or stack[-1][0] != {')': '(', '}': '{', ']': '['}[char]:
                    return
                stack.pop()
    if stack:
        return
    for block in callables:
        if names[block.entity.qualified_name] != 1:
            continue
        start = block.start
        header = method_header(masked, start) if block.owner else top_level_callable_header(masked, start)
        if header is None or header.name != block.entity.name:
            continue
        if block.owner:
            matches = [c for c in containers if c.name == block.owner and c.start < start < c.end]
            if owners[block.owner] != 1 or len(matches) != 1 or matches[0].kind != 'component':
                continue
            if scopes[start] != (('{', matches[0].start),):
                continue
        elif scopes[start]:
            continue
        line = masked[start].strip()
        if line.startswith('@'):
            match = re.match(r'@Builder\s+(?!@)', line)
            if not match or '@' in line[match.end():].split('(', 1)[0]:
                continue
            decorator_line = start
        else:
            decorator_line = start - 1
            if decorator_line < 0 or masked[decorator_line].strip() != '@Builder':
                continue
        previous = decorator_line - 1
        while previous >= 0 and not masked[previous].strip():
            previous -= 1
        if previous >= 0:
            prior = masked[previous].strip()
            # A prior closing argument list may belong to a stacked decorator.
            if prior.startswith('@') or prior.endswith(')'):
                continue
        # Existing full method range/key remains unchanged; positive role only.
        block.entity.callable_roles.append('arkts_builder')
