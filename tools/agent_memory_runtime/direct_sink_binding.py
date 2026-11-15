# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Finite single-hop static parameter receipts, not runtime/dataflow analysis."""
from __future__ import annotations

import hashlib
import re
import sqlite3
from pathlib import Path
from typing import Any

from .log_api_catalog import ECMA_LANGUAGES, parse_log_api_call
from .code_wiki_extractors import language_for
from .required_source_reads import (
    RequiredSourceReadError, source_expectation, source_read_failed,
)

MAX_SOURCE_BYTES = 2 * 1024 * 1024
_IDENTIFIER = r'[A-Za-z_$][A-Za-z0-9_$]*'
_LITERAL = r'''(?:'[^'\\\r\n]*'|"[^"\\\r\n]*")'''
_SIMPLE = rf'(?:{_LITERAL}|{_IDENTIFIER}|[+-]?(?:\d+(?:\.\d*)?|\.\d+))'
_HEADER = rf'(?:public\s+|private\s+|protected\s+)?(?P<name>{_IDENTIFIER})\s*\((?P<params>[^()]*)\)\s*(?::\s*void\s*)?\{{(?P<body>[\s\S]*)\}}'
_PARAM = re.compile(rf'({_IDENTIFIER})\s*:\s*(string|number|boolean)')
_RESERVED = {'this', 'super', 'arguments', 'eval', 'void', 'class', 'function',
             'let', 'const', 'var', 'return', 'new', 'yield', 'await'}


def source_snapshot(root: Path, relative: str, cache: dict) -> tuple[str, str] | None:
    """At most one bounded read/file/rebuild; retain required-read failure semantics."""
    key = ('source', relative)
    if key not in cache:
        cache[key] = None
        path = root / relative
        expected = source_expectation(path)
        try:
            if not path.resolve().is_relative_to(root.resolve()):
                return None
            with path.open('rb') as stream:
                raw = stream.read(MAX_SOURCE_BYTES + 1)
        except OSError as error:
            source_read_failed(path, error)
            return None
        source_expectation(path)
        if len(raw) > MAX_SOURCE_BYTES:
            if expected is not None:
                raise RequiredSourceReadError(f'required log binding source exceeds bound: {path}')
            return None
        digest = hashlib.sha256(raw).hexdigest()
        if expected is not None and (not expected[0] or digest != expected[0]):
            raise RequiredSourceReadError(f'required log binding source changed: {path}')
        try:
            text = raw.decode('utf-8').replace('\r\n', '\n').replace('\r', '\n')
        except UnicodeDecodeError:
            return None
        cache[key] = (digest, text)
    return cache[key]


def _row(conn: sqlite3.Connection, project_id: str, table: str, identity: int, cache: dict):
    key = (table, identity)
    if key not in cache:
        row = conn.execute(f'SELECT * FROM {table} WHERE project_id=? AND id=?',
                           (project_id, identity)).fetchone()
        cache[key] = dict(row) if row else None
    return cache[key]


def _method(row: dict, text: str):
    lines = text.splitlines()
    start, end = int(row.get('start_line') or 0), int(row.get('end_line') or 0)
    if not 0 < start <= end <= len(lines) or end - start > 200:
        return None
    match = re.fullmatch(_HEADER, '\n'.join(lines[start-1:end]).strip())
    if not match or match['name'] != row.get('symbol'):
        return None
    return match


def _arguments(raw: str) -> list[str] | None:
    # Full lexical consumption: commas inside quoted literals are not separators.
    match = re.fullmatch(rf'this\.({_IDENTIFIER})\s*\(([\s\S]*)\)', raw.strip())
    if not match:
        return None
    text = match[2].strip()
    result = []
    while text:
        part = re.match(_SIMPLE, text)
        if not part:
            return None
        result.append(part[0])
        text = text[part.end():].lstrip()
        if text:
            if not text.startswith(',') or not text[1:].strip():
                return None
            text = text[1:].lstrip()
    return result


def direct_message_binding(conn: sqlite3.Connection, project_id: str, root: Path,
                           item: dict[str, Any], raw_call: str, cache: dict) -> str | None:
    """None means legacy scope. Symbolic template means direct binding unproved."""
    language = language_for(Path(str(item.get('sink_file_path', ''))))
    parsed = parse_log_api_call(str(item.get('sink_statement') or ''), language)
    if (language not in ECMA_LANGUAGES or not parsed or item.get('wrapper_depth') != 1
            or item.get('evidence_class') != 'static_wrapped'
            or item.get('file_path') != item.get('sink_file_path')
            or item.get('file_path') != item.get('wrapper_file_path')):
        return None
    # Canonical sink args must be complete simple expressions, no parser guess.
    sink_args = _arguments('this.api(' + parsed.args_text + ')')
    if not sink_args or parsed.message_argument >= len(sink_args):
        return None
    parameter = sink_args[parsed.message_argument]
    if not re.fullmatch(_IDENTIFIER, parameter):
        return None
    fallback = str(item.get('sink_template') or '')
    if fallback != '{' + parameter + '}':
        return None
    caller = _row(conn, project_id, 'code_symbols', int(item.get('caller_id') or 0), cache)
    wrapper = _row(conn, project_id, 'code_symbols', int(item.get('wrapper_id') or 0), cache)
    sink = _row(conn, project_id, 'code_log_statements', int(item.get('sink_log_id') or 0), cache)
    if not caller or not wrapper or not sink:
        return fallback
    owner = wrapper.get('owner_name')
    if not owner or caller.get('owner_name') != owner:
        return fallback
    snapshot = source_snapshot(root, str(item['file_path']), cache)
    if not snapshot:
        return fallback
    digest, text = snapshot
    generation = item.get('index_generation')
    if (not isinstance(generation, int) or generation <= 0
            or item.get('source_digest') != digest
            or any(r.get('source_digest') != digest or r.get('index_generation') != generation
                   or r.get('file_path') != item['file_path'] for r in (caller, wrapper, sink))):
        return fallback
    if (caller.get('symbol') != item.get('caller') or wrapper.get('symbol') != item.get('wrapper')
            or any(not r.get('symbol_key') or r.get('qualified_name') != f"{owner}.{r['symbol']}"
                   for r in (caller, wrapper))
            or sink.get('function') != wrapper['symbol']
            or sink.get('raw_statement') != item.get('sink_statement')
            or sink.get('message_template') != fallback
            or sink.get('logger') != parsed.logger or sink.get('level') != parsed.level):
        return fallback
    # A typed edge already identifies this sink. Verify it, not its spelling alone.
    edges = conn.execute('''SELECT relation FROM memory_edges WHERE project_id=?
        AND valid_to IS NULL AND ((source_type='code_symbol' AND source_id=?
        AND target_type='code_symbol' AND target_id=? AND relation='calls') OR
        (source_type='code_symbol' AND source_id=? AND target_type='code_log_statement'
        AND target_id=? AND relation='emits_log'))''',
        (project_id, caller['id'], wrapper['id'], wrapper['id'], sink['id'])).fetchall()
    if {r['relation'] for r in edges} != {'calls', 'emits_log'}:
        return fallback
    uniqueness = conn.execute('''SELECT count(*) FROM code_symbols WHERE project_id=?
        AND file_path=? AND owner_name=? AND symbol=?''',
        (project_id, item['file_path'], owner, wrapper['symbol'])).fetchone()[0]
    if uniqueness != 1:
        return fallback
    wm, cm = _method(wrapper, text), _method(caller, text)
    if not wm or not cm or cm['params'].strip():
        return fallback
    if not re.fullmatch(re.escape(raw_call) + r'\s*;?', cm['body'].strip()):
        return fallback
    if not raw_call.startswith('this.' + wrapper['symbol'] + '('):
        return fallback
    names = []
    for spec in wm['params'].split(','):
        match = _PARAM.fullmatch(spec.strip())
        if not match or match[1] in _RESERVED:
            return fallback
        names.append(match[1])
    if not names or len(names) > 8 or len(set(names)) != len(names) or parameter not in names:
        return fallback
    receiver = str(item['sink_statement']).strip().split('.')[0]
    if receiver in names:
        return fallback
    classes = conn.execute('''SELECT start_line,end_line FROM code_symbols
        WHERE project_id=? AND file_path=? AND symbol=? AND symbol_type='class' ''',
        (project_id, item['file_path'], owner)).fetchall()
    if len(classes) != 1:
        return fallback
    class_start, class_end = classes[0]['start_line'], classes[0]['end_line']
    lines = text.splitlines()
    if not (0 < class_start <= wrapper['start_line'] <= wrapper['end_line'] <= class_end <= len(lines)
            and class_start <= caller['start_line'] <= caller['end_line'] <= class_end):
        return fallback
    owner_body = '\n'.join(lines[class_start-1:class_end])
    if re.search(rf'(?m)^\s*(?:(?:public|private|protected|static|readonly)\s+)*{re.escape(receiver)}\s*[:=]', owner_body):
        return fallback
    call_line = int(item.get('line') or 0)
    if not (caller['start_line'] <= call_line <= caller['end_line']) or lines[call_line-1].strip().rstrip(';') != raw_call.strip():
        return fallback
    body = wm['body'].strip()
    prefix = re.match(rf'(?:(?:void\s+{_IDENTIFIER})\s*;?\s*)*', body)[0]
    if any(name not in names for name in re.findall(rf'void\s+({_IDENTIFIER})', prefix)):
        return fallback
    if body[len(prefix):].strip().rstrip(';').strip() != str(item['sink_statement']).strip().rstrip(';'):
        return fallback
    sink_line = int(sink.get('line') or 0)
    lines = text.splitlines()
    if not (wrapper['start_line'] <= sink_line <= wrapper['end_line']) or lines[sink_line-1].strip().rstrip(';') != str(item['sink_statement']).strip().rstrip(';'):
        return fallback
    args = _arguments(raw_call)
    if args is None or len(args) != len(names):
        return fallback
    actual = args[names.index(parameter)]
    if not re.fullmatch(_LITERAL, actual):
        return fallback
    return actual[1:-1]
