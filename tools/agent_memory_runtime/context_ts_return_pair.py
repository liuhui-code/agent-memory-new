"""Retain admitted TS source for a statically witnessed returned-value pair."""
import hashlib
import json
from pathlib import Path
import re
import sqlite3

from .context_recovery_append import _candidate
from .context_source_excerpt import safe_source_path
from .ecma_callable_headers import method_header
from .ecma_field_scope import verified_depth_lines
from .ecma_parameter_properties import MEMBER, written_receiver
from .performance_scoring import estimate_payload_tokens
from .query_language import COMPARISON_CLAUSE_RE, NEGATIVE_RESULT_CLAUSE_RE
from .query_target_scope import SINGLE_TARGET_RE, classify_target_scope, permits_cross_file_portfolio
from .source_call_scanner import balanced_call_end, code_mask
from .storage import connect

NAME = r'[A-Za-z_$][A-Za-z0-9_$]*'
LITERAL = r"""(?:'[^'\\\r\n]*'|"[^"\\\r\n]*"|\d+|true|false|null)"""
INIT = re.compile(rf'\s*const (?P<local>{NAME})\s*=\s*await\s+this\.(?P<field>{NAME})\.(?P<callee>{NAME})\s*\(')
END = re.compile(rf'\s*(?:(?:this\.(?P<slot>{NAME})\s*=\s*(?P<direct>{NAME})\.{NAME})|'
                 rf'(?:this\.(?P<setter>{NAME})\((?P<forward>{NAME})\.{NAME}\)))\s*;'
                 rf'\s*return this\.(?P<result>{NAME})\s*;\s*')


def eligible(query, raw):
    handoff = raw.get('query_handoff') or {}
    anchors = handoff.get('code_anchors') or []
    return (type(raw) is dict and type(handoff) is dict and len(query) <= 240
            and not any(pattern.search(query) for pattern in (SINGLE_TARGET_RE, COMPARISON_CLAUSE_RE, NEGATIVE_RESULT_CLAUSE_RE))
            and permits_cross_file_portfolio(classify_target_scope(query))
            and raw.get('source_freshness', {}).get('status') == 'current'
            and not handoff.get('log_anchors') and not (handoff.get('path_context') or {}).get('activated')
            and len(anchors) == 2 and len({a.get('file_path') for a in anchors}) == 2
            and all(a.get('source') == 'wiki' and a.get('symbol_type') == 'class'
                    and a.get('record_type') == 'code_symbol'
                    and not any(a.get(k) for k in ('log_identity_match', 'graph_relation', 'graph_neighbor', 'identity_match'))
                    and str(a.get('file_path') or '').endswith('.ts') for a in anchors)
            and (handoff.get('callable_evidence') or {}).get('certainty') == 'bounded')


def source_snapshot(project, anchor, files, rows, generation):
    path = anchor['file_path']
    file = safe_source_path(Path(project.root).resolve(), path)
    if file is None or file.suffix != '.ts':
        return None
    with file.open('rb') as stream:
        raw = stream.read(32769)
    if len(raw) > 32768 or b'\0' in raw or b'\r' in raw or b'`' in raw:
        return None
    text = raw.decode('utf-8')
    if any(c in text for c in '\v\f\x1c\x1d\x1e\x85\u2028\u2029'):
        return None
    lines = text.split('\n')
    digest = hashlib.sha256(raw).hexdigest()
    owner = [r for r in rows if r.get('id') == anchor['record_id'] and r.get('symbol') == anchor.get('symbol')]
    if (len(owner) != 1 or len(files) != 1 or any(
            r.get('index_generation') != generation or r.get('source_digest') != digest for r in (owner[0], files[0]))):
        return None
    row = owner[0]
    lo, hi = row['start_line'], row['end_line']
    if (row.get('file_path') != path or row.get('symbol_type') != 'class' or row.get('owner_name')
            or row.get('qualified_name') != row.get('symbol')
            or (lo, hi) != (anchor.get('start_line'), anchor.get('end_line'))
            or not 0 < lo <= hi <= len(lines)
            or not re.fullmatch(rf'\s*(?:export )?class {re.escape(row["symbol"])}\s*\{{\s*', lines[lo-1])):
        return None
    return row, text, lines, digest


def owned_method(row, owner, digest):
    return (row.get('file_path') == owner['file_path'] and row.get('owner_name') == owner['symbol']
            and row.get('qualified_name') == owner['symbol'] + '.' + str(row.get('symbol'))
            and row.get('symbol_type') in {'function', 'method'} and row.get('owner_kind') == 'class'
            and row.get('source_digest') == digest and row.get('index_generation') == owner.get('index_generation')
            and row.get('evidence_class') in {'static', 'exact'}
            and str(row.get('semantic_adapter')).startswith('typescript-static@')
            and type(row.get('start_line')) is int and type(row.get('end_line')) is int
            and owner['start_line'] < row['start_line'] <= row['end_line'] < owner['end_line'])


def body(lines, method):
    start, end = method['start_line']-1, method['end_line']
    head = method_header(lines, start)
    if head is None or head.name != method['symbol'] or not head.body_start:
        return None
    # Body is exact, explicit straight-line source, without ASI inference.
    header = lines[start]
    if not header.rstrip().endswith('{') or lines[end-1].strip() != '}':
        return None
    return '\n'.join(lines[start+1:end-1]), head.params


def witnesses(snapshot, rows):
    owner, _, lines, digest = snapshot
    source = lines[owner['start_line']-1:owner['end_line']]
    owner_text = '\n'.join(source)
    owner_code = code_mask(owner_text)
    depth = verified_depth_lines(owner_code.split('\n'), ('{',))
    if not depth:
        return []
    direct = [source[i] for i in depth if i != len(source) - 1 and source[i].strip()]
    constructor = [line for line in direct if re.match(r'\s*constructor\s*\(', line)]
    if (len(constructor) != 1 or not re.fullmatch(
            rf'\s*constructor\s*\(\s*(?:(?:private|public|protected)\s+)?readonly\s+{NAME}\s*:\s*{NAME}\s*\)\s*\{{\s*\}}\s*',
            constructor[0])
            or any(re.match(r"""\s*[@#\['"]|\s*(?:(?:public|private|protected)\s+)*(?:get|set|static)\s+""", line)
                   for line in direct)):
        return []
    members = [(m['name'], line) for line in direct if (m := MEMBER.match(line))]
    methods = [r for r in rows if owned_method(r, owner, digest)]
    found = []
    for method in methods:
        part = body(lines, method)
        if part is None:
            continue
        em = read(part[0])
        if em is None:
            continue
        span, field, name, arity, slot, setter = em
        fields = [line for member, line in members if member == slot]
        if len(fields) != 1 or not re.fullmatch(rf'\s*{re.escape(slot)}\s*=\s*{LITERAL}\s*;\s*', fields[0]):
            continue
        sink = None
        if setter:
            if (sum(member == setter for member, _ in members) != 1 or written_receiver(setter, owner_code)
                    or not sole_own_reference(owner_text, owner_code, setter)):
                # A shared sink cannot identify which caller the request means.
                continue
            if re.search(r'\bthis\s*\[', owner_code):
                continue
            sink = copies_slot(lines, methods, setter, slot)
            if sink is None:
                continue
        offset = sum(len(line.encode('utf-8'))+1 for line in lines[:method['start_line']])
        byte_span = tuple(offset + len(part[0][:i].encode('utf-8')) for i in span)
        found.append((method, method['start_line'] + 1 + part[0].count('\n', 0, span[0]),
                      byte_span, field, name, arity, sink))
    return found


def sole_own_reference(text, mask, name):
    spelling = rf'(?<![\w$]){re.escape(name)}(?![\w$])'
    # Name declaration + exact proved call only. Comments and quoted spellings
    # are counted conservatively; a syntactic absence is not global closure.
    return (len(re.findall(spelling, text)) == 2
            and len(re.findall(rf'\bthis\s*\.\s*{spelling}', mask)) == 1)


def copies_slot(lines, methods, name, slot):
    matching = [r for r in methods if r['symbol'] == name]
    if len(matching) != 1:
        return None
    method = matching[0]
    if not re.fullmatch(rf'\s*{re.escape(name)}\s*\([^\r\n]+\)(?:\s*:\s*void)?\s*\{{\s*', lines[method['start_line']-1]):
        return None
    part = body(lines, method)
    if part is None:
        return None
    argument = re.fullmatch(rf'\s*({NAME})\s*:\s*(?:string|number|boolean)\s*', part[1])
    if argument and re.fullmatch(rf'\s*this\.{re.escape(slot)}\s*=\s*{re.escape(argument[1])}\s*;\s*', part[0]):
        return method
    return None


def read(text):
    binds = {}
    cursor = 0
    for _ in range(8):
        m = INIT.match(text, cursor)
        if m is None:
            break
        args_end = balanced_call_end(code_mask(text), m.end()-1)
        if args_end is None or not re.fullmatch(rf'\s*(?:{LITERAL})?\s*', text[m.end():args_end-1]):
            return None
        if text[args_end:args_end+1] != ';' or m['local'] in binds:
            return None
        start = m.start('field') - len('this.')
        binds[m['local']] = ((start, args_end), m['field'], m['callee'],
                             bool(text[m.end():args_end-1].strip()))
        cursor = args_end+1
    end = END.fullmatch(text, cursor)
    if end is None or end['slot'] not in (None, end['result']):
        return None
    local = end['direct'] or end['forward']
    return (*binds[local], end['result'], end['setter']) if local in binds else None


def edge_proof(conn, project, source, target, line, field, arity, digest):
    rows = conn.execute("""SELECT relation,evidence,evidence_kind,extractor_version FROM memory_edges
        WHERE project_id=? AND source_type='code_symbol' AND source_id=? AND target_type='code_symbol'
          AND target_id=? AND valid_to IS NULL AND relation IN ('calls','awaits')""",
        (project.project_id, source['id'], target['id'])).fetchall()
    seen = set()
    for relation, evidence, kind, version in rows:
        ev = json.loads(evidence)
        suffix = 'call; field=' + field + '; arity=' if relation == 'calls' else 'await; field=' + field
        wanted = 'typed constructor property ' + suffix
        detail = str(ev.get('detail'))
        if (ev.get('schema_version') == 'semantic-evidence/v1' and ev.get('language') == 'TypeScript'
                and kind == 'static_semantic_' + relation and ev.get('adapter') == source.get('semantic_adapter')
                and version == 'semantic-index:v1/' + ev['adapter'] and ev.get('evidence_class') == 'static'
                and ev.get('line') == line and ev.get('source_digest') == digest
                and ((relation == 'calls' and detail == wanted + str(int(arity)))
                     or (relation == 'awaits' and detail == wanted))):
            seen.add(relation)
    return seen == {'calls','awaits'}


def retain(project, query, raw, baseline):
    try:
        if not eligible(query, raw):
            return baseline
        return _retain(project, raw, baseline)
    except (KeyError, TypeError, ValueError, OSError, OverflowError, AttributeError, sqlite3.Error):
        return baseline


def same_callable(evidence, method):
    return (evidence.get('file_path') == method['file_path']
            and evidence.get('symbol') == method['symbol']
            and evidence.get('owner_name') == method['owner_name']
            and evidence.get('owner_kind') == method['owner_kind']
            and evidence.get('source_range') == {'start_line':method['start_line'], 'end_line':method['end_line'],
                                                 'selection_reason':'callable_symbol_range'})


def _retain(project, raw, baseline):
    from .context_budget import synchronize_estimate
    handoff = baseline['query_handoff']
    selected = handoff['code_anchors']
    if (len(selected) != 1 or handoff.get('log_anchors') or handoff.get('relation_hints')
            or handoff.get('path_context', {}).get('activated')
            or baseline['source_freshness'].get('status') != 'current'
            or baseline['output_budget'] != {'estimated_tokens': estimate_payload_tokens(baseline),
                                             'target_tokens': 1500, 'truncated': False}):
        return baseline
    anchors = raw['query_handoff']['code_anchors']
    consumer = next((a for a in anchors if selected[0].get('file_path') == a['file_path']), None)
    if not consumer or selected[0].get('record_ids') != [consumer['record_id']]:
        return baseline
    producer = next(a for a in anchors if a is not consumer)
    generation = baseline['source_freshness']['generation']
    with connect(project) as conn:
        def rows(table, a):
            return [dict(r) for r in conn.execute(
                f'SELECT * FROM {table} WHERE project_id=? AND file_path=? LIMIT 65',
                (project.project_id,a['file_path']))]
        cm, pm = rows('code_symbols',consumer), rows('code_symbols',producer)
        if max(len(cm),len(pm)) >= 65:
            return baseline
        c = source_snapshot(project, consumer, rows('code_files',consumer), cm, generation)
        p = source_snapshot(project, producer, rows('code_files',producer), pm, generation)
        if c is None or p is None:
            return baseline
        findings = witnesses(c, cm)
        if len(findings) != 1:
            return baseline
        method, line, span, field, name, arity, sink = findings[0]
        # A class anchor is not a request for any method in the class.
        # Tie the witness to the serving primary, either directly or at its
        # verified own forwarding method. Do not authorize from audit seeds.
        primary = (handoff.get('callable_evidence') or {}).get('primary') or {}
        if not any(same_callable(primary, row) for row in (method, sink) if row is not None):
            return baseline
        if not c[1].encode('utf-8')[slice(*span)].startswith(f'this.{field}.{name}'.encode()):
            return baseline
        if not any(e['start_line'] <= c[0]['start_line'] <= c[0]['end_line'] <= e['end_line']
                   and e['content'] == '\n'.join(c[2][e['start_line']-1:e['end_line']])
                   and e['truncated'] is False for e in selected[0].get('source_excerpts', [])):
            return baseline
        methods = [r for r in pm if r.get('symbol') == name and owned_method(r, p[0], p[3])]
        if len(methods) != 1 or not edge_proof(conn, project, method, methods[0], line, field, arity, c[3]):
            return baseline
    target = methods[0]
    ev = raw['query_handoff']['callable_evidence']
    admitted = [a for a in ev.get('alternatives', []) if same_callable(a, target)]
    if len(admitted) != 1:
        return baseline
    start,end = target['start_line'],target['end_line']
    anchor = {'file_path': target['file_path'], 'symbol': target['symbol'], 'symbol_type': target['symbol_type'],
              'record_type': 'code_symbol', 'record_id': target['id'], 'start_line': start, 'end_line': end}
    excerpt = {'symbol': target['symbol'], 'start_line':start,'end_line':end,
               'content':'\n'.join(p[2][start-1:end]),'source':'current_worktree',
               'selection_reason':'verified_return_value_pair','focus_line':None,'truncated':False}
    candidate = _candidate(baseline, [{'anchor':anchor,'excerpt':excerpt}])
    if candidate is None:
        return baseline
    added = candidate['query_handoff']['code_anchors'][-1]
    added.update(role='expansion', read_window={'start_line':start,'end_line':end})
    synchronize_estimate(candidate)
    return candidate if candidate['output_budget']['estimated_tokens'] <= 1500 else baseline
