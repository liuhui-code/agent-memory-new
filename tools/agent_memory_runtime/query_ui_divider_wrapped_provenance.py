"""Current visible depth-one log provenance, never runtime dispatch authority."""
import json
import sqlite3
from pathlib import PurePosixPath
from .storage import connect
from .semantic_models import symbol_key
from .query_output_loop_selection import snapshot, valid_row
from .query_ui_divider_method_scope import read_current
from .query_ui_divider_negative import negative_log_conflict


def positive(value):
    return type(value) is int and value > 0


def path_ok(value):
    return (type(value) is str and bool(value) and '#' not in value and '\\' not in value
            and not PurePosixPath(value).is_absolute()
            and all(p not in ('', '.', '..') for p in value.split('/')))


def one(db, table, clause, args):
    rows = [dict(r) for r in db.execute('SELECT * FROM '+table+' WHERE '+clause+' LIMIT 2', args)]
    if len(rows) != 1:
        raise ValueError('ambiguous or missing '+table)
    return rows[0]


def current(db, project, row, witnesses):
    if (not positive(row.get('id')) or row.get('project_id') != project.project_id
            or not path_ok(row.get('file_path')) or not positive(row.get('index_generation'))):
        raise ValueError('invalid current row')
    file = one(db, 'code_files', 'project_id=? AND file_path=?', (project.project_id, row['file_path']))
    if (not positive(file.get('id')) or not positive(file.get('index_generation'))
            or row.get('source_digest') != file.get('source_digest')
            or row['index_generation'] != file['index_generation']):
        raise ValueError('stale row')
    source = read_current(project, file)
    if source is None:
        raise ValueError('stale bytes')
    witnesses.append(dict(file=file, source_digest=file['source_digest']))
    return source


def method(db, project, file, name, line, witnesses):
    if not positive(line) or type(name) is not str or not name:
        raise ValueError('invalid method reference')
    # Do not choose smallest containing range among namesakes.
    row = one(db, 'code_symbols', 'project_id=? AND file_path=? AND symbol=? AND symbol_type=?',
              (project.project_id, file, name, 'function'))
    if not valid_row(row, project) or not row['start_line'] <= line <= row['end_line']:
        raise ValueError('invalid method identity/range')
    language = {'arkts-static': 'ArkTS', 'typescript-static': 'TypeScript'}[row['semantic_adapter'].partition('@')[0]]
    if (type(row.get('signature')) is not str or not row['signature']
            or row['symbol_key'] != symbol_key(language, file, row['qualified_name'], row['signature'])):
        raise ValueError('noncanonical symbol key')
    alias = one(db, 'code_symbols', 'project_id=? AND (id=? OR symbol_key=?)',
                (project.project_id, row['id'], row['symbol_key']))
    if alias != row:
        raise ValueError('method alias')
    source = current(db, project, row, witnesses)
    if row['end_line'] > len(source.splitlines()):
        raise ValueError('method outside source')
    return row


def three(value):
    parsed = json.loads(value)
    if type(parsed) is not list or len(parsed) != 3 or any(type(v) is not str or not v for v in parsed):
        raise ValueError('unknown path')
    return parsed


def wrapped(db, project, log, negative_files, index):
    if (not positive(log.get('effect_id')) or not positive(log.get('log_id'))
            or not positive(log.get('line')) or type(log.get('wrapper_depth')) is not int
            or log['wrapper_depth'] != 1 or log.get('truncated') is not False):
        raise ValueError('unsupported effect shape')
    effect = one(db, 'code_log_effects', 'project_id=? AND id=?', (project.project_id, log['effect_id']))
    if (not positive(effect.get('id')) or not positive(effect.get('sink_log_id'))
            or not positive(effect.get('line')) or type(effect.get('wrapper_depth')) is not int
            or effect['wrapper_depth'] != 1 or type(effect.get('truncated')) is not int
            or effect['truncated'] != 0 or effect.get('evidence_class') not in ('static_wrapped', 'inferred_wrapped')):
        raise ValueError('unsupported stored effect')
    for field in ('file_path', 'function', 'wrapper_symbol', 'logger', 'message_template', 'evidence_class'):
        if type(effect.get(field)) is not str or type(log.get(field)) is not str or effect[field] != log[field]:
            raise ValueError('effect projection')
    if effect['line'] != log['line'] or effect['sink_log_id'] != log['log_id']:
        raise ValueError('effect projection identity')
    if 'level' in log and (type(log['level']) is not str or log['level'] != effect.get('level')):
        raise ValueError('optional level projection')
    paths, locations = three(effect['call_path']), three(effect['call_path_locations'])
    if (type(log.get('call_path')) is not list or type(log.get('call_path_locations')) is not list
            or paths != log['call_path'] or locations != log['call_path_locations']):
        raise ValueError('effect projection paths')
    refs = []
    for location in locations:
        if location.count('#') != 1:
            raise ValueError('unknown location')
        file, name = location.split('#')
        if not path_ok(file) or not name:
            raise ValueError('unsafe location')
        refs.append((file, name))
    if (type(effect.get('level')) is not str or not effect['level'] or not effect['logger']
            or paths != [effect['function'], effect['wrapper_symbol'], effect['logger']+'.'+effect['level']]
            or refs[0] != (effect['file_path'], effect['function']) or [n for _, n in refs] != paths):
        raise ValueError('location identity')
    sink = one(db, 'code_log_statements', 'project_id=? AND id=?', (project.project_id, effect['sink_log_id']))
    if (not positive(sink.get('id')) or not positive(sink.get('line'))
            or any(type(sink.get(k)) is not str or not sink[k] for k in ('function', 'logger', 'level', 'message_template', 'raw_statement'))
            or (sink['logger'], sink['level']) != (effect['logger'], effect['level'])
            or refs[1] != (sink['file_path'], sink['function'])
            or refs[2] != (sink['file_path'], sink['logger']+'.'+sink['level'])):
        raise ValueError('sink identity')
    if {f for f, _ in refs} & negative_files:
        raise ValueError('negative file conflict')
    witnesses = []
    current(db, project, effect, witnesses)
    current(db, project, sink, witnesses)
    caller = method(db, project, effect['file_path'], effect['function'], effect['line'], witnesses)
    wrapper = method(db, project, sink['file_path'], sink['function'], sink['line'], witnesses)
    calls = one(db, 'memory_edges', 'project_id=? AND source_type=? AND source_id=? AND relation=? AND target_type=? AND target_id=? AND valid_to IS NULL',
                (project.project_id, 'code_symbol', caller['id'], 'calls', 'code_symbol', wrapper['id']))
    emit = one(db, 'memory_edges', 'project_id=? AND source_type=? AND source_id=? AND relation=? AND target_type=? AND target_id=? AND valid_to IS NULL',
               (project.project_id, 'code_symbol', wrapper['id'], 'emits_log', 'code_log_statement', sink['id']))
    for edge in (calls, emit):
        if (not positive(edge.get('id')) or not positive(edge.get('source_id')) or not positive(edge.get('target_id'))
                or edge.get('project_id') != project.project_id or not edge.get('valid_from')
                or edge.get('source_revision') != index.get('source_revision')):
            raise ValueError('edge identity')
    evidence = json.loads(calls['evidence'])
    inferred = effect['evidence_class'] == 'inferred_wrapped'
    if (type(evidence) is not dict or evidence.get('schema_version') != 'semantic-evidence/v1'
            or type(evidence.get('line')) is not int or evidence['line'] != effect['line']
            or evidence.get('source_digest') != effect['source_digest']
            or calls.get('evidence_kind') != ('inferred_semantic_calls' if inferred else 'static_semantic_calls')
            or evidence.get('evidence_class') != ('inferred' if inferred else 'static')
            or calls.get('extractor_version') != 'semantic-index:v1/'+caller['semantic_adapter']
            or emit.get('extractor_version') != 'code-wiki:v4'
            or emit.get('evidence_kind') != 'code_observability'
            or emit.get('evidence') != sink['file_path']+':'+str(sink['line'])):
        raise ValueError('unknown edge evidence')
    return dict(effect=effect, sink=sink, caller=caller, wrapper=wrapper, calls=calls, emits=emit, files=witnesses)


def wrapped_negative_provenance(project, data, frames):
    """Return bound witnesses or None. Does not bypass any query/source/output guard."""
    try:
        info = json.loads(frames)
        if (type(info) is not dict or info.get('contract') != 'multilingual-negative-static-divider/v1'
                or type(info['descriptor']['excluded_names']) is not list or not info['descriptor']['excluded_names']):
            return None
        logs = data['query_handoff']['log_anchors']
        if type(logs) is not list:
            return None
        negative_files = set()
        for item in info['negative_identities']:
            if item['declaration'] is not None:
                file = item['declaration']['file_path']
                if not path_ok(file):
                    return None
                negative_files.add(file)
        witnesses = []
        with connect(project) as db:
            db.execute('BEGIN')
            index = one(db, 'code_index_state', 'project_id=?', (project.project_id,))
            graph = one(db, 'graph_runtime_state', 'project_id=?', (project.project_id,))
            if (index.get('status') != 'active' or not positive(index.get('generation')) or not positive(graph.get('graph_revision'))
                    or type(index.get('source_revision')) is not str or not index['source_revision']
                    or index.get('extractor_version') != 'code-derived:v1'):
                return None
            for log in logs:
                if type(log) is not dict:
                    return None
                if log.get('evidence_class') == 'direct' and log.get('effect_id') is None:
                    if negative_log_conflict({'query_handoff': {'log_anchors': [log]}}, frames):
                        return None
                else:
                    witnesses.append(wrapped(db, project, log, negative_files, index))
        return snapshot(dict(contract='visible-current-depth1-negative-files/v1', frames=frames, logs=logs,
                             witnesses=witnesses, index_state=index, graph_state=graph))
    except (AttributeError, KeyError, TypeError, ValueError, OSError, UnicodeError, sqlite3.Error, OverflowError):
        return None
