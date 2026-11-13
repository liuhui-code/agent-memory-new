# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

"""Bounded producer proof, distinct from searchable identifier/string tokens."""
import re
from pathlib import Path
from .callable_behavior_hints import NON_CODE_RE
from .arkts_behavior_markers import RUNTIME_CAPABILITY_RE
from .semantic_ecma_mechanisms import PERSISTENCE_CALL_RE, PERSISTENCE_RECEIVER_RE, READ_METHOD_RE


def source_operation_roles(source: str, file_path: str) -> list[str]:
    if Path(file_path).suffix not in {".ts", ".ets"}:
        return []
    if '`' in source:
        return ['source_operation_checked:v2.1', 'source_operation_unresolved:runtimecapability', 'source_operation_unresolved:persistenceread']
    code = NON_CODE_RE.sub(lambda match: ' ' * len(match.group()), source)
    if '{' not in code or code.count('{') != code.count('}'):
        return []
    body = code.partition('{')[2]
    nested = re.search(r'\b(?!(?:if|for|while|switch|catch|with)\b)[A-Za-z_$][\w$]*\s*\([^)]*\)\s*(?::[^{};]+)?\{', body)
    result = []
    runtime_calls = list(RUNTIME_CAPABILITY_RE.finditer(body))
    shadowed = re.search(r'\b(?:const|let|var|function|class)\s+(?:bundleManager|canIUse|hasSystemCapability)\b', code)
    shadowed = shadowed or re.search(r'\b(?:bundleManager|canIUse|hasSystemCapability)\b', code.partition('{')[0])
    names = r'(?:bundleManager|canIUse|hasSystemCapability)'
    # Destructuring and reassignment invalidate this bounded name-shape witness;
    # absence of these patterns is still not resolved platform API identity.
    shadowed = shadowed or re.search(
        r'\b(?:const|let|var)\s*[\[{][^;=]*\b' + names + r'\b', code,
    ) or re.search(
        r'[\[{][^;=]*\b' + names + r'\b[^;=]*[\]}]\s*=', body,
    ) or re.search(
        r'\b' + names + r'\s*(?:=(?!=|>)|[+*/%&|^-]=|\?\?=|\|\|=|&&=|\+\+|--)', body,
    )
    qualified_other = any(match.start() and body[:match.start()].rstrip().endswith('.') for match in runtime_calls)
    if runtime_calls and (shadowed or qualified_other):
        result.append('source_operation_unresolved:runtimecapability')
    elif runtime_calls:
        result.append('source_operation:runtimecapability')
    elif re.search(r'\b(?:bundleManager|canIUse|hasSystemCapability)\b', body):
        result.append('source_operation_unresolved:runtimecapability')
    calls = PERSISTENCE_CALL_RE.findall(body)
    reads = [(receiver, method) for receiver, method in calls if READ_METHOD_RE.match(method)]
    direct_reads = [receiver for receiver, _ in reads
                    if PERSISTENCE_RECEIVER_RE.search(receiver.rsplit('.', 1)[-1])]
    if direct_reads:
        result.append('source_operation:persistenceread')
    # Dynamic/optional syntax is not absence; this scanner does not resolve it.
    if '?.' in body or re.search(r'\]\s*\(', body):
        result.append('source_operation_unresolved:persistenceread')
    persistence_reference = any(PERSISTENCE_RECEIVER_RE.search(name)
                                for name in re.findall(r'[A-Za-z_$][\w$]*', body))
    unknown_read_receiver = len(direct_reads) != len(reads)
    if unknown_read_receiver or (persistence_reference and not direct_reads):
        result.append('source_operation_unresolved:persistenceread')
    if not body or '=>' in body or '/' in body or nested or re.search(r'\b(?:function|class)\b', body):
        return ['source_operation_checked:v2.1', *[value.replace('source_operation:', 'source_operation_unresolved:') for value in result]]
    return ['source_operation_checked:v2.1', *result]
