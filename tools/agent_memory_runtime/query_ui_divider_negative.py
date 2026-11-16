"""Exact declaration exclusions and unchanged-query log obligations, never log deletion."""
import json
from .storage import connect
from .query_output_loop_selection import valid_row
from .query_command_table_scope import IDENTITY, FILE_FIELDS
from .query_ui_divider_method_scope import read_current
from .ui_divider_source import tokenize, Unknown
from .semantic_callable_profile import owner_kind



def exact_negative_declaration(source, row):
    try:
        tokens, pairs = tokenize(source)
        matches = []
        depth = 0
        for index, token in enumerate(tokens):
            if token.kind == 'punct' and token.value in ('{', '(', '['):
                depth += 1
            elif token.kind == 'punct' and token.value in ('}', ')', ']'):
                depth -= 1
            elif depth == 0 and token.kind == 'name' and token.value in ('class', 'struct'):
                if index+1 < len(tokens) and tokens[index+1].kind == 'name' and tokens[index+1].value == row['symbol']:
                    if (index+2 >= len(tokens) or tokens[index+2].kind != 'punct' or tokens[index+2].value != '{'
                            or (token.value == 'class') != (row['symbol_type'] == 'class')):
                        return False
                    matches.append((token.line, tokens[pairs[index+2]].line))
        return matches == [(row['start_line'], row['end_line'])]
    except (Unknown, ValueError, TypeError, KeyError, IndexError):
        return False

def resolve_negative_declarations(project, names):
    resolved = []; files = []
    with connect(project) as db:
        for name in names:
            rows = [dict(r) for r in db.execute('SELECT * FROM code_symbols WHERE project_id=? AND symbol=? LIMIT 3', (project.project_id, name))]
            if not rows:
                resolved.append(dict(name=name, declaration=None)); continue
            if len(rows) != 1:
                return None
            row = rows[0]
            if (row.get('symbol_type') not in {'class', 'component', 'struct'} or not valid_row(row, project)
                    or row.get('owner_name') not in {'', None} or row.get('qualified_name') != name
                    or row.get('owner_kind') != owner_kind(name, row['symbol_type'], row['file_path'])):
                return None
            aliases = [dict(r) for r in db.execute('SELECT * FROM code_symbols WHERE project_id=? AND (id=? OR symbol_key=?) LIMIT 2',
                                                  (project.project_id, row['id'], row['symbol_key']))]
            if len(aliases) != 1:
                return None
            fs = [dict(r) for r in db.execute('SELECT * FROM code_files WHERE project_id=? AND file_path=? LIMIT 2', (project.project_id, row['file_path']))]
            if (len(fs) != 1 or type(fs[0].get('id')) is not int or fs[0]['id'] <= 0
                    or fs[0].get('project_id') != project.project_id or fs[0]['source_digest'] != row['source_digest']
                    or fs[0]['index_generation'] != row['index_generation']):
                return None
            source = read_current(project, fs[0])
            if (source is None or not 0 < row['start_line'] <= row['end_line'] <= len(source.splitlines())
                    or not exact_negative_declaration(source, row)):
                return None
            resolved.append(dict(name=name, declaration={k: row[k] for k in IDENTITY}, file={k: fs[0][k] for k in FILE_FIELDS}))
            files.append((row['file_path'], row['source_digest']))
    return resolved, tuple(sorted(set(files)))


def negative_log_conflict(data, frame_snapshot):
    try:
        info = json.loads(frame_snapshot)
        if not isinstance(info, dict) or info.get('contract') != 'multilingual-negative-static-divider/v1':
            return False
        negatives = [r['declaration'] for r in info['negative_identities'] if r['declaration'] is not None]
        logs = data['query_handoff']['log_anchors']
        if type(logs) is not list:
            return True
        for log in logs:
            if (type(log) is not dict or log.get('evidence_class') != 'direct'
                    or log.get('effect_id') is not None
                    or not isinstance(log.get('file_path'), str) or not log['file_path']
                    or type(log.get('line')) is not int or log['line'] <= 0):
                return True
            # Unknown mediated relations cannot be silently separated from a named
            # declaration. No wrapper/path inference or transfer of log authority.
            if any(log.get(k) for k in ('wrapper_symbol', 'wrapper_depth', 'call_path', 'call_path_locations')):
                return True
            for declaration in negatives:
                if log.get('file_path') != declaration['file_path']:
                    continue
                line = log.get('line')
                if type(line) is not int or line <= 0 or declaration['start_line'] <= line <= declaration['end_line']:
                    return True
        return False
    except (ValueError, TypeError, KeyError, AttributeError):
        return True


def exclusion_intersection(anchors, resolved):
    for item in resolved:
        declaration = item['declaration']
        if declaration is None:
            continue
        for anchor in anchors:
            if anchor['file_path'] != declaration['file_path']:
                continue
            for excerpt in anchor['source_excerpts']:
                if max(excerpt['start_line'], declaration['start_line']) <= min(excerpt['end_line'], declaration['end_line']):
                    return True
    return False
