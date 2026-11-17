# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Pass-local absence capture from actual complete collector lanes, not DB proof."""
from dataclasses import dataclass
from pathlib import Path
import weakref

_issued = {}


@dataclass(frozen=True)
class NoLogCapture:
    project_id: str
    root: str
    database: str
    query: str
    retrieval: str
    collection_id: int


def values(capture):
    return (capture.project_id, capture.root, capture.database, capture.query,
            capture.retrieval, capture.collection_id)


def capture_validation_no_logs(project, query, retrieval, collection, direct, effects):
    from .query_validation_field_request import validation_field_request
    # A second observation of the same object must not reuse an older empty seal.
    _issued.pop(id(collection), None)
    if validation_field_request(query) is None:
        return
    from .query_collect import CollectedMatches
    from .query_language import positive_retrieval_query
    if (type(collection) is not CollectedMatches or type(direct) is not list
            or type(effects) is not list or direct or effects
            or retrieval != positive_retrieval_query(query)):
        return
    capture = NoLogCapture(project.project_id, str(Path(project.root).resolve()),
                           str(Path(project.db_path).resolve()), query, retrieval, id(collection))
    key = id(collection)
    def remove(reference):
        entry = _issued.get(key)
        if entry is not None and entry[0] is reference:
            _issued.pop(key, None)
    reference = weakref.ref(collection, remove)
    _issued[key] = (reference, capture, values(capture))


def validation_no_logs(project, query, collection):
    from .query_validation_field_request import validation_field_request
    from .query_language import positive_retrieval_query
    from .query_collect import CollectedMatches
    try:
        entry = _issued.get(id(collection))
        if (validation_field_request(query) is None or type(collection) is not CollectedMatches
                or entry is None or entry[0]() is not collection
                or type(collection.matches) is not dict
                or collection.matches.get('code_log_matches') != []):
            return None
        capture = entry[1]
        expected = (project.project_id, str(Path(project.root).resolve()),
                    str(Path(project.db_path).resolve()), query, positive_retrieval_query(query), id(collection))
        if type(capture) is not NoLogCapture or values(capture) != entry[2] or entry[2] != expected:
            return None
        return capture
    except (AttributeError, TypeError, ValueError, OSError):
        return None


def check_validation_no_logs(project, query, collection, capture):
    return capture is not None and validation_no_logs(project, query, collection) is capture
