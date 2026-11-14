# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Offline source-fact experiment. Not imported by runtime or a semantic schema."""
import hashlib
import json
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
D = Path(__file__).resolve().parent
sys.path.insert(0, str(D.parents[2]))
from tools.agent_memory_runtime.ecma_callback_mask import callback_mask_lines
from tools.agent_memory_runtime.ecma_callable_headers import method_header
from tools.agent_memory_runtime.semantic_ecma import parse_containers, parse_container_members

IDENT = r'[A-Za-z_$][A-Za-z0-9_$]*'

@dataclass(frozen=True)
class Witness:
    version: str
    source: dict
    formal: dict
    argument_call: dict
    callback: dict
    invocation: dict


def pairs(text):
    stack, result = [], {}
    for i, c in enumerate(text):
        if c in '([{':
            stack.append((c, i))
            if len(stack) > 32:
                return None
        elif c in ')]}':
            if not stack or stack[-1][0] != {')': '(', ']': '[', '}': '{'}[c]:
                return None
            _, opening = stack.pop()
            result[opening] = i
    return None if stack else result


def parameters(text):
    if not text.strip():
        return []
    parts = text.split(',')
    if len(parts) > 16:
        return None
    rows = []
    for part in parts:
        m = re.fullmatch(r'\s*(' + IDENT + r')\s*:\s*(' + IDENT + r')\s*', part)
        if not m or m[1] == 'this':
            return None
        rows.append((m[1], m[2]))
    return rows if len({n for n, _ in rows}) == len(rows) else None


def pieces(text, opening, closing, balanced):
    result, start, i = [], opening + 1, opening + 1
    while i < closing:
        if i in balanced:
            i = balanced[i] + 1
        elif text[i] == ',':
            result.append((start, i)); start = i = i + 1
        else:
            i += 1
    if text[start:closing].strip():
        result.append((start, closing))
    return result


def extract(source, path):
    if len(source.encode()) > 32768:
        return [], ['file-cap']
    lines = source.splitlines()
    masked = callback_mask_lines(lines)
    if masked is None:
        return [], ['lexical-unknown']
    text = '\n'.join(masked)
    balanced = pairs(text)
    if balanced is None:
        return [], ['balance-unknown']
    offsets = [0]
    for line in masked[:-1]:
        offsets.append(offsets[-1] + len(line) + 1)
    containers = parse_containers(lines, 'ArkTS', path)
    counts = Counter(c.name for c in containers)
    methods = []
    for container in containers:
        if counts[container.name] != 1 or container.kind != 'class':
            continue
        # Module-level plain class only; no generic/expression/namespace scope.
        head = masked[container.start].strip()
        if not re.fullmatch(r'(?:export\s+)?class\s+' + IDENT + r'\s*\{', head):
            continue
        pos = offsets[container.start]
        if any(a < pos <= b for a, b in balanced.items()):
            continue
        found, _ = parse_container_members(lines, 'ArkTS', path, container, False, None)
        methods.extend(found)
    if len(methods) > 128:
        return [], ['method-cap']
    identities = Counter(m.entity.qualified_name for m in methods)
    result, skipped = [], []
    for block in methods:
        name = block.entity.qualified_name
        h = method_header(masked, block.start)
        if identities[name] != 1 or h is None or h.body_start is None:
            skipped.append(name + ':header-unknown'); continue
        params = parameters(h.params)
        if params is None or len({t for _, t in params}) != len(params):
            skipped.append(name + ':formal-unknown'); continue
        start = offsets[h.body_start[0]] + h.body_start[1]
        end = balanced.get(start)
        if end is None or text[start] != '{':
            skipped.append(name + ':body-unknown'); continue
        body = text[start+1:end]
        call = re.fullmatch(r'\s*(' + IDENT + r')\.(' + IDENT + r')\s*\(\s*(\{.*\})\s*\)\s*;?\s*', body, re.S)
        if not call or call[1] not in dict(params):
            skipped.append(name + ':not-supported-argument-call'); continue
        obj = start + 1 + call.start(3)
        obj_end = balanced.get(obj)
        if obj_end != start + call.end(3):
            skipped.append(name + ':object-unknown'); continue
        members = pieces(text, obj, obj_end, balanced)
        local = []
        for left, right in members:
            prop = re.fullmatch(r'\s*(' + IDENT + r')\s*:\s*\(([^()]*)\)\s*=>\s*(\{.*\})\s*', text[left:right], re.S)
            if prop is None:
                break
            args = parameters(prop[2])
            if args is None or set(dict(args)) & set(dict(params)):
                break
            cb = left + prop.start(3)
            cb_end = balanced.get(cb)
            if cb_end != left + prop.end(3) - 1:
                break
            inv = re.fullmatch(r'\s*(' + IDENT + r')\.(' + IDENT + r')\s*\(([^()]*)\)\s*;?\s*', text[cb+1:cb_end])
            if inv is None or inv[1] not in dict(params) or inv[1] == call[1]:
                break
            values = [v.strip() for v in inv[3].split(',')] if inv[3].strip() else []
            if any(v not in dict(args) for v in values):
                break
            local.append(Witness('offline-callback-source/v1',
                {'file_path': path, 'symbol_key': block.entity.key,
                 'qualified_name': name, 'signature': block.entity.signature,
                 'start_line': block.start+1, 'end_line': block.end+1,
                 'source_digest': hashlib.sha256(source.encode()).hexdigest(),
                 'coordinate_unit': 'newline-normalized decoded character, half-open'},
                {'index': next(i for i,p in enumerate(params) if p[0] == inv[1]),
                 'name': inv[1], 'declared_type': dict(params)[inv[1]]},
                {'receiver': call[1], 'member': call[2], 'range': [start+1+call.start(1), end], 'object_range': [obj, obj_end+1]},
                {'property': prop[1], 'range': [left+prop.start(1), right], 'body_range': [cb, cb_end+1]},
                {'receiver': inv[1], 'member': inv[2], 'range': [cb+1+inv.start(1), cb+1+inv.end(3)+1]}))
        else:
            if 0 < len(local) <= 16:
                result.extend(asdict(w) for w in local)
                continue
        skipped.append(name + ':callback-or-receiver-unknown')
    return result, skipped


def validate_witness(fact, case):
    # Independent shape/source checks; no runtime authority or selector use.
    from tools.agent_memory_runtime.semantic_models import symbol_key
    src = fact['source']; source = case['source']
    lines = source.splitlines(); masked = '\n'.join(callback_mask_lines(lines))
    assert src['file_path'] == case['file_path']
    assert src['source_digest'] == case['sha256']
    assert src['symbol_key'] == symbol_key('ArkTS', src['file_path'], src['qualified_name'], src['signature'])
    first,last = src['start_line'],src['end_line']
    assert type(first) is int and type(last) is int and 0 < first <= last <= len(lines)
    header = method_header(callback_mask_lines(lines), first-1)
    assert header is not None and header.name == src['qualified_name'].rsplit('.',1)[-1]
    ps = parameters(header.params); formal = fact['formal']
    assert type(formal['index']) is int and 0 <= formal['index'] < len(ps)
    assert ps[formal['index']] == (formal['name'],formal['declared_type'])
    outer = [sum(len(v)+1 for v in lines[:first-1]),sum(len(v)+1 for v in lines[:last])-1]
    ranges = [fact['argument_call']['range'],fact['argument_call']['object_range'],fact['callback']['range'],fact['callback']['body_range'],fact['invocation']['range']]
    previous = outer
    for span in ranges:
        assert all(type(x) is int for x in span) and previous[0] <= span[0] < span[1] <= previous[1]
        previous = span
    call,obj,prop,body,inv = [masked[a:b] for a,b in ranges]
    assert call.lstrip().startswith(fact['argument_call']['receiver']+'.'+fact['argument_call']['member'])
    assert obj.startswith('{') and obj.endswith('}') and body.startswith('{') and body.endswith('}')
    assert prop.lstrip().startswith(fact['callback']['property']+':')
    assert re.fullmatch(re.escape(formal['name'])+r'\.'+re.escape(fact['invocation']['member'])+r'\s*\([^()]*\)',inv)


def main():
    protocol = json.loads((D/'protocol.json').read_text())
    output = []
    for case in protocol['cases']:
        assert hashlib.sha256(case['source'].encode()).hexdigest() == case['sha256']
        facts, unknown = extract(case['source'], case['file_path'])
        validation_errors = []
        for f in facts:
            try:
                validate_witness(f, case)
            except (AssertionError, KeyError, TypeError, ValueError) as error:
                validation_errors.append(type(error).__name__+':'+str(error))
        actual = [[f['source']['qualified_name'],f['formal']['declared_type'],f['callback']['property'],f['invocation']['member']] for f in facts]
        output.append({'id':case['id'], 'expected':case['expected'], 'actual':actual,
                       'pass':sorted(actual)==sorted(case['expected']) and not validation_errors, 'validation_errors':validation_errors, 'witnesses':facts, 'unknown':unknown})
    (D/'results.json').write_text(json.dumps(output, indent=2))
    print(json.dumps({'passed':sum(r['pass'] for r in output),'total':len(output),'failures':[r['id'] for r in output if not r['pass']]}))

if __name__ == '__main__':
    main()
