# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Unconnected, finite validation collector capture; never serving permission."""
from dataclasses import dataclass
import json
import math
from pathlib import Path, PurePosixPath
import sqlite3
import weakref

MAX_DEPTH = 12
MAX_NODES = 16384
MAX_SCALAR_BYTES = 16384
MAX_BYTES = 1048576
MAX_ROWS = 64
MAX_COLUMNS = 128
MAX_KEY_BYTES = 128
_issued = {}


def _text_size(value, ceiling=MAX_SCALAR_BYTES):
    if type(value) is not str or len(value) > ceiling:
        return None
    try:
        size = len(value.encode('utf-8'))
        return size if size <= ceiling else None
    except UnicodeError:
        return None


def _scalar(value):
    kind = type(value)
    if value is None or kind is bool:
        return 0
    if kind is int:
        return 0 if value.bit_length() <= 64 else None
    if kind is float:
        return 0 if math.isfinite(value) else None
    if kind is str:
        return _text_size(value)
    return None


def bounded_metadata(value):
    """Exact builtins only; root depth 0; count shared occurrences, reject cycles.

    Dict key bytes count toward the same byte ceiling, not the value-node count.
    Nodes are reserved before adding children to keep traversal itself bounded.
    No JSON/repr/custom iteration or recursive copy precedes these checks.
    """
    stack = [(value, 0, False)]
    active = set()
    nodes = 1
    byte_count = 0
    while stack:
        item, depth, leaving = stack.pop()
        if leaving:
            active.remove(id(item))
            continue
        if depth > MAX_DEPTH:
            return False
        kind = type(item)
        if kind not in (dict, list):
            size = _scalar(item)
            if size is None:
                return False
            byte_count += size
            if byte_count > MAX_BYTES:
                return False
            continue
        if id(item) in active:
            return False
        nodes += len(item)
        if nodes > MAX_NODES:
            return False
        active.add(id(item))
        stack.append((item, depth, True))
        if kind is dict:
            for key, child in item.items():
                size = _text_size(key)
                if size is None:
                    return False
                byte_count += size
                if byte_count > MAX_BYTES:
                    return False
                stack.append((child, depth + 1, False))
        else:
            for child in item:
                stack.append((child, depth + 1, False))
    return True


def _direct_rows(rows):
    """Whitelist real SQLite records, validating scalar shape before extraction."""
    staged = []
    byte_count = 0
    nodes = 1 + len(rows)
    for row in rows:
        if type(row) is not sqlite3.Row or len(row) > MAX_COLUMNS:
            return None
        keys = row.keys()
        if len(keys) != len(row):
            return None
        seen = set()
        values = []
        nodes += len(keys)
        if nodes > MAX_NODES:
            return None
        for index, key in enumerate(keys):
            size = _text_size(key, MAX_KEY_BYTES)
            if size is None or key in seen:
                return None
            seen.add(key)
            scalar = row[index]
            scalar_size = _scalar(scalar)
            if scalar_size is None:
                return None
            byte_count += size + scalar_size
            if byte_count > MAX_BYTES:
                return None
            values.append(scalar)
        staged.append((keys, values))
    # No arbitrary Mapping coercion; all rows/columns/scalars are checked above.
    return [{key: value for key, value in zip(keys, values)} for keys, values in staged]


def _identity(project, query, retrieval, collection):
    from .models import Project
    if type(project) is not Project or type(query) is not str or type(retrieval) is not str:
        return None
    if (type(project.project_id) is not str or type(project.root) is not type(Path())
            or type(project.db_path) is not type(Path())):
        return None
    result = [project.project_id, str(Path(project.root).resolve()),
              str(Path(project.db_path).resolve()), query, retrieval, id(collection)]
    return tuple(result) if bounded_metadata(result) else None


def _encode(value):
    if not bounded_metadata(value):
        return None
    # Input consists exclusively of prechecked bounded builtins.
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), sort_keys=True)


def _positive_id(value):
    return type(value) is int and 0 < value and value.bit_length() <= 64


def _lane_identities(inventory):
    for name in ('direct', 'effects'):
        seen = set()
        for row in inventory[name]:
            if type(row) is not dict or not _positive_id(row.get('id')) or row['id'] in seen:
                return False
            seen.add(row['id'])
    return True


def _scope_paths(collection):
    rows = collection.matches.get('wiki_matches')
    if type(rows) is not list or not rows:
        return None
    paths = set()
    for row in rows:
        if type(row) is not dict:
            return None
        path = row.get('file_path')
        if type(path) is not str or not path:
            return None
        canonical = PurePosixPath(path)
        if canonical.is_absolute() or '..' in canonical.parts or str(canonical) != path:
            return None
        paths.add(path)
        if len(paths) > 12:
            return None
    return sorted(paths)


@dataclass(frozen=True, eq=False)
class ValidationLogCapture:
    """Opaque identity handle. Attributes are not source authority."""
    collection_id: int


def capture_validation_logs(project, query, retrieval, collection, direct, effects):
    """Capture complete actual lanes; caller must be collector (not wired yet).

    Every attempted recapture revokes the previous handle, even on rejection.
    Local caller lists are detached, never retained as mutable authority.
    """
    key = id(collection)
    _issued.pop(key, None)
    from .query_collect import CollectedMatches
    from .query_language import positive_retrieval_query
    from .query_validation_field_request import validation_field_request
    try:
        if (type(collection) is not CollectedMatches or type(direct) is not list
                or type(effects) is not list or not 0 < len(direct) + len(effects) <= MAX_ROWS
                or validation_field_request(query) is None
                or retrieval != positive_retrieval_query(query)):
            return None
        # Reject custom effect records before any copying/JSON conversion.
        if any(type(row) is not dict for row in effects):
            return None
        converted = _direct_rows(direct)
        if converted is None:
            return None
        inventory = {'direct': converted, 'effects': effects}
        identity = _identity(project, query, retrieval, collection)
        if identity is None or not _lane_identities(inventory):
            return None
        # Existing whole collection data must also be finite before snapshot.
        state = {'matches': collection.matches, 'recall_audit': collection.recall_audit}
        aggregate = {'identity': list(identity), 'inventory': inventory, 'state': state}
        if not bounded_metadata(aggregate):
            return None
        paths = _scope_paths(collection)
        if paths is None:
            return None
        # Full collector paths are only a primitive resource upper bound, not
        # later gated source-pool authorization. Never crop or augment them.
        inventory['scope_paths'] = paths
        if not bounded_metadata(aggregate):
            return None
        inventory_seal = _encode(inventory)
        state_seal = _encode(state)
        if inventory_seal is None or state_seal is None:
            return None
        capture = ValidationLogCapture(key)
        def retire(reference):
            entry = _issued.get(key)
            if entry is not None and entry[0] is reference:
                _issued.pop(key, None)
        reference = weakref.ref(collection, retire)
        _issued[key] = (reference, capture, identity, inventory_seal, state_seal)
        return None
    except (AttributeError, TypeError, ValueError, OSError, UnicodeError, OverflowError):
        return None


def _validated_entry(project, capture):
    from .query_collect import CollectedMatches
    from .query_language import positive_retrieval_query
    from .query_validation_field_request import validation_field_request
    if type(capture) is not ValidationLogCapture:
        return None
    entry = _issued.get(capture.collection_id)
    if entry is None or entry[1] is not capture:
        return None
    collection = entry[0]()
    if type(collection) is not CollectedMatches or id(collection) != capture.collection_id:
        return None
    identity = entry[2]
    query, retrieval = identity[3:5]
    if (validation_field_request(query) is None or positive_retrieval_query(query) != retrieval
            or _identity(project, query, retrieval, collection) != identity):
        return None
    state = {'matches': collection.matches, 'recall_audit': collection.recall_audit}
    # No recursive resnapshot of mutated collection state before finite check.
    if _encode(state) != entry[4]:
        return None
    return entry


def validation_logs(project, query, collection):
    """Return only an authentic, unchanged, same-pass identity handle."""
    from .query_collect import CollectedMatches
    try:
        if type(collection) is not CollectedMatches:
            return None
        entry = _issued.get(id(collection))
        if entry is None or entry[0]() is not collection or type(query) is not str:
            return None
        if query != entry[2][3] or _validated_entry(project, entry[1]) is not entry:
            return None
        return entry[1]
    except (AttributeError, TypeError, ValueError, OSError, UnicodeError, OverflowError):
        return None


def validation_log_inventory(project, capture):
    """Authenticated detached inventory for the separate provenance verifier.

    Registry strings are immutable; return values can never mutate the seal.
    All source freshness/edges/raw projection still require that verifier.
    """
    try:
        entry = _validated_entry(project, capture)
        if entry is None:
            return None
        inventory = json.loads(entry[3])
        inventory['query'] = entry[2][3]
        inventory['retrieval'] = entry[2][4]
        return inventory
    except (AttributeError, TypeError, ValueError, OSError, UnicodeError, OverflowError):
        return None
