"""Add bounded source-path wiki search hints, never owner or body assertions."""
from copy import deepcopy
import re
import sqlite3
from .context_graph_field_navigation import qualify_graph_field_navigation
from .context_budget import synchronize_estimate
from .performance_scoring import estimate_payload_tokens
from .validation_field_source import Unknown

_PATH = re.compile(r'[A-Za-z0-9_-]+(?:/[A-Za-z0-9_.-]+)+\.(?:ts|ets)', re.ASCII)


def append_graph_field_followup(project, original, payload):
    if type(payload) is not dict:
        return payload
    budget = payload.get('output_budget')
    if type(budget) is not dict or type(budget.get('target_tokens')) is not int or budget['target_tokens'] != 1500:
        return payload
    try:
        hints = payload['query_handoff']['next_queries']
        if type(hints) is not list or len(hints) >= 3 or any(type(h) is not str or len(h) > 100 for h in hints):
            return payload
        qualified = qualify_graph_field_navigation(project, original, payload)
        if not qualified:
            return payload
        return _append_qualified_hints(payload, qualified)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, AttributeError,
            sqlite3.Error, Unknown, RecursionError):
        return payload


def _append_qualified_hints(payload, qualified):
    hints = payload['query_handoff']['next_queries']
    if type(hints) is not list or len(hints) >= 3 or any(type(h) is not str or len(h) > 100 for h in hints):
        return payload
    paths = list(dict.fromkeys(a['file_path'] for a in qualified))
    if any(type(p) is not str or len(p) > 100 or not _PATH.fullmatch(p)
           or any(part in {'.', '..'} for part in p.split('/')) for p in paths):
        return payload
    new = [p for p in paths if p not in hints]
    if not new or len(hints) + len(new) > 3:
        return payload
    trial = deepcopy(payload)
    trial['query_handoff']['next_queries'].extend(new)
    synchronize_estimate(trial)
    return trial if estimate_payload_tokens(trial) <= 1500 else payload
