# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Bounded static identity for this.field calls through named type aliases."""
import re
from collections import Counter
from .ecma_callback_mask import callback_mask_lines
from .ecma_field_scope import verified_masked_field_lines
from .ecma_import_alias import alias_bindings
from .semantic_models import SemanticRelation
from .source_call_scanner import scan_calls_masked, call_argument_count


ROOT_CALL = r'(?<![\w$.])this\.([A-Za-z_$][\w$]*)\.([A-Za-z_$][\w$]*)\s*\('


def typed_alias_bindings(lines, containers, fields_by_owner, imports):
    aliases = alias_bindings(imports)
    if not aliases:
        return {}
    paths = {alias: path for _name, alias, path in imports}
    full_mask = callback_mask_lines(lines)
    if full_mask is None:
        return {}
    whole_code = '\n'.join(full_mask)
    if '=>' in whole_code:
        return {}
    top_level, stack = [], []
    pairs = {')': '(', ']': '[', '}': '{'}
    for line in full_mask:
        top_level.append(not stack)
        for char in line:
            if char in '([{':
                stack.append(char)
            elif char in ')]}':
                if not stack or stack.pop() != pairs[char]:
                    return {}
    if stack:
        return {}
    result = {}
    owner_counts = Counter(owner.name for owner in containers)
    for owner in containers:
        if (owner.kind not in {'class', 'component'} or owner_counts[owner.name] != 1
                or not top_level[owner.start]):
            continue
        field_lines = verified_masked_field_lines(full_mask[owner.start:owner.end + 1])
        if field_lines is None:
            continue
        header = '\n'.join(full_mask[owner.start:owner.end + 1]).partition('{')[0]
        bindings = {}
        for field, alias in fields_by_owner.get(owner.name, {}).items():
            if alias not in aliases:
                continue
            original, path = aliases[alias], paths.get(alias)
            if not original or not path or re.search(r'\b' + re.escape(alias) + r'\b', header):
                continue
            if re.search(r'\b(?:class|interface|type|enum)\s+' + re.escape(alias) + r'\b', whole_code):
                continue
            # Old field maps truncate composite types; require a bare declaration.
            declarations = [line for line in field_lines if re.match(
                r'^\s*(?:(?:public|private|protected|readonly|static)\s+)*' + re.escape(field) + r'\s*:', line)]
            bare = r'^\s*(?:(?:public|private|protected|readonly|static)\s+)*' + re.escape(field) + r'\s*:\s*' + re.escape(alias) + r'\s*;?\s*$'
            if len(declarations) == 1 and re.fullmatch(bare, declarations[0]):
                bindings[field] = (original, path)
        if bindings:
            result[owner.name] = bindings
    return result


def aliased_field_relations(lines, block, context):
    bindings = context.typed_alias_fields.get(block.owner or '', {})
    if not bindings:
        return []
    body = '\n'.join(lines[block.start:block.end + 1])
    masked = callback_mask_lines(body.splitlines())
    if masked is None:
        return []
    code = '\n'.join(masked)
    if re.search(r'\bthis\s*:|\bstatic\b', code.partition('{')[0]):
        return []
    # Only straight-line own bodies. Nested receivers/scopes remain unknown.
    if (code.count('{') != 1 or code.count('}') != 1 or '=>' in code
            or re.search(r'\b(?:function|class)\b|\.\s*this\s*\.', code)):
        return []
    result = []
    for relative_line, call in scan_calls_masked(body, code, ROOT_CALL):
        field, method = re.search(ROOT_CALL, call).groups()
        if field not in bindings:
            continue
        original, path = bindings[field]
        result.append(SemanticRelation(
            source_key=block.entity.key, relation='calls', target_name=method,
            target_qualified_name=f'{original}.{method}', target_file_path=path,
            line=block.start + relative_line, confidence=0.9,
            detail=f'aliased typed field call; field={field}; arity={call_argument_count(call)}'))
    for match in re.finditer(r'\bawait\s+' + ROOT_CALL, code):
        field, method = match.groups()
        if field not in bindings:
            continue
        original, path = bindings[field]
        result.append(SemanticRelation(
            source_key=block.entity.key, relation='awaits', target_name=method,
            target_qualified_name=f'{original}.{method}', target_file_path=path,
            line=block.start + 1, confidence=0.9,
            detail=f'aliased typed field await; field={field}'))
    return result
