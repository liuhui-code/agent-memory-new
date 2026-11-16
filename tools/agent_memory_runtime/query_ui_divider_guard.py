"""Exact adjective-slot distinction, preserving full-query log obligations."""
from .query_record_loop_selection import protected_record_loop
from .query_ui_divider_request import divider_identity_query
from .log_event_identity import event_match
from .query_log_owner_admission import independently_named_log_owner


def protected_divider(data, query, pool, *, pending=False):
    try:
        identity_query = divider_identity_query(query)
        # The actual pool and identity/graph/path flags are never projected.
        if protected_record_loop(data, identity_query, pool, pending=pending):
            return True
        if identity_query != query:
            # Dropping the adjective can erase an exact event phrase. Retain
            # every event and log-owner obligation from the complete query.
            for log in data['query_handoff']['log_anchors']:
                if event_match(log, query)['priority'] > 0 or independently_named_log_owner(log, query):
                    return True
        return False
    except (AttributeError, KeyError, TypeError, ValueError):
        return True
