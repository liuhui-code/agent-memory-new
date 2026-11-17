"""Private snapshot-bound trial handoff; no persistent capability or source proof."""
from copy import deepcopy
from pathlib import Path
from dataclasses import dataclass
import json
import sqlite3
import weakref
from .storage import connect
from .query_output_loop_selection import snapshot

_ISSUER = object()


_LOG_ISSUER = object()
_LOG_ISSUANCES = {}


@dataclass(frozen=True)
class LogCandidates:
    project_id: str
    root: str
    query: str
    retrieval: str
    direct: tuple
    effects: tuple
    issuer: object

    def __copy__(self): return dict(direct=self.direct, effects=self.effects)
    def __deepcopy__(self, memo): return self.__copy__()


def capture_log_candidates(project, query, retrieval, direct, effects):
    from .query_touch_index_request import touch_index_request
    if not touch_index_request(query):return None
    capture = LogCandidates(project.project_id, str(project.root.resolve()), query, retrieval,
                            tuple(snapshot(dict(r)) for r in direct),
                            tuple(snapshot(dict(r)) for r in effects), _LOG_ISSUER)
    key = id(capture)
    reference = weakref.ref(capture, lambda ref: _LOG_ISSUANCES.pop(key, None))
    _LOG_ISSUANCES[key] = (reference, _log_values(capture))
    return capture


def _log_values(capture):
    return (capture.project_id, capture.root, capture.query, capture.retrieval,
            capture.direct, capture.effects)


def _issued_log_capture(capture):
    if type(capture) is not LogCandidates or capture.issuer is not _LOG_ISSUER:
        return False
    entry = _LOG_ISSUANCES.get(id(capture))
    values = _log_values(capture)
    return (entry is not None and entry[0]() is capture
            and all(type(v) is str for v in values[:4])
            and all(type(v) is tuple and all(type(r) is str for r in v) for v in values[4:])
            and entry[1] == values)


def log_candidate_rows(project, query, capture):
    try:
        from .query_language import positive_retrieval_query
        if (not _issued_log_capture(capture)
                or capture.project_id != project.project_id or capture.root != str(project.root.resolve())
                or capture.query != query or capture.retrieval != positive_retrieval_query(query)
                or type(capture.direct) is not tuple or type(capture.effects) is not tuple):
            return None
        result = {name: [json.loads(r) for r in getattr(capture, name)] for name in ('direct', 'effects')}
        return result if all(type(r) is dict for rows in result.values() for r in rows) else None
    except (AttributeError, ValueError, TypeError):
        return None


class PassCaptures(list):
    def __init__(self):
        super().__init__(); self.logs = []


def capture_touch_pass(collection, pool, captures):
    captures.append(deepcopy(pool))
    if type(captures) is PassCaptures:
        captures.logs.append(collection._private_log_capture)


def begin_touch_pass(project, query):
    from .query_touch_index_request import touch_index_request
    return (trial_state(project), PassCaptures()) if touch_index_request(query) else (None, None)


def logs_signature(capture):
    if capture is None: return None
    if not _issued_log_capture(capture): raise ValueError('capture issuance')
    return (capture.project_id, capture.root, capture.query, capture.retrieval, capture.direct, capture.effects)


def trial_state(project):
    try:
        with connect(project) as db:
            db.execute('BEGIN')
            tables = {name: [dict(r) for r in db.execute(
                'SELECT * FROM ' + name + ' WHERE project_id=?', (project.project_id,))]
                for name in ('code_index_state', 'graph_runtime_state')}
            files = [dict(r) for r in db.execute(
                'SELECT id,project_id,file_path,source_digest,index_generation FROM code_files '
                'WHERE project_id=? ORDER BY id', (project.project_id,))]
        if len(tables['code_index_state']) != 1: return None
        return snapshot(dict(project=project.project_id, root=str(Path(project.root).resolve()),
                             states=tables, files=files))
    except (OSError, ValueError, sqlite3.Error):
        return None


class TouchTrial(dict):
    def __copy__(self): return dict(self)
    def __deepcopy__(self, memo): return deepcopy(dict(self), memo)


def binding(data):
    return (data._query, data._state, data._baseline_signature,
            snapshot(dict(data)), snapshot(data._pool), logs_signature(data._baseline_logs), logs_signature(data._trial_logs))


def make_touch_trial(project, query, baseline, trial, pool, state, baseline_logs=None, trial_logs=None):
    from .query_touch_index_request import touch_index_request
    if (not touch_index_request(query) or state is None or trial_state(project) != state
            or type(pool) is not list or any(type(r) is not dict for r in pool)
            or type(trial) is not dict or type(baseline) is not dict
            or any(d.get('query') != query or d.get('project_id') != project.project_id
                   or d.get('project_path') != str(project.root) for d in (baseline, trial))):
        return None
    if any(log_candidate_rows(project, query, c) is None for c in (baseline_logs, trial_logs)):
        return None
    data = TouchTrial(trial)
    data._query = query; data._state = state; data._issuer = _ISSUER
    data._baseline_signature = snapshot(baseline); data._pool = deepcopy(pool)
    data._baseline_logs = baseline_logs; data._trial_logs = trial_logs
    data._binding = binding(data)
    return data


def valid_trial(project, query, data):
    from .query_touch_index_request import touch_index_request
    try:
        return (type(data) is TouchTrial and data._issuer is _ISSUER
                and touch_index_request(query) and data._query == query
                and all(log_candidate_rows(project, query, c) is not None
                        for c in (data._baseline_logs, data._trial_logs))
                and data._binding == binding(data)
                and trial_state(project) == data._state)
    except (AttributeError, TypeError, ValueError, OSError, sqlite3.Error):
        return False


def bind_touch_pass(project, query, baseline, result, explicit_intent, state, context_pass, baseline_capture=None):
    from .query_touch_index_selection import bind_touch_index_context
    if state is None or type(result) is not dict or trial_state(project) != state:
        return result
    captured = PassCaptures()
    trial = context_pass(project, query, explicit_intent, allow_touch_recall=True, touch_capture=captured)
    if (len(captured) != 1 or len(captured.logs) != 1 or type(baseline_capture) is not PassCaptures
            or len(baseline_capture) != 1 or len(baseline_capture.logs) != 1): return result
    bound = make_touch_trial(project, query, baseline, trial, captured[0], state,
                             baseline_capture.logs[0], captured.logs[0])
    return bind_touch_index_context(project, query, baseline, bound) if bound is not None else result
