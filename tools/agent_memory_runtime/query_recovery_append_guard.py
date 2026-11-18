# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Complete incidental-direct-log protection; no validation authority reuse."""
from .query_recovery_pair import recovery_request
from .query_record_loop_selection import protected_record_loop
from .query_validation_field_log_guards import FLAGS, IDENTITY, RAW_KEYS, scored_schema_rejections
from .query_validation_log_capture import bounded_metadata
from .log_event_identity import event_match
from .query_log_owner_admission import independently_named_log_owner


def admitted(query, raw, pool, collection, inventory):
    if (not recovery_request(query) or type(raw) is not dict or type(pool) is not list
            or not bounded_metadata([raw, pool, collection.matches, collection.recall_audit, inventory])
            or protected_record_loop(raw, query, pool)):
        return False
    if type(inventory) is not dict or inventory.get('effects') != []:
        return False
    direct = inventory.get('direct')
    if type(direct) is not list or not direct:
        return False
    def complete_audit(value):
        if type(value) is dict:
            for key, part in value.items():
                if key in ('saturated', 'broad_saturated', 'fallback_skipped_for_scale') and part is not False:
                    return False
                if not complete_audit(part):
                    return False
        elif type(value) is list:
            return all(complete_audit(part) for part in value)
        return True
    if not complete_audit(collection.recall_audit):
        return False
    members = {}
    for row in direct:
        if (type(row) is not dict or type(row.get('id')) is not int or row['id'] in members
                or event_match(row, query)['priority'] > 0
                or independently_named_log_owner(row, query) or any(row.get(k) for k in FLAGS)):
            return False
        members[row['id']] = row
    scored = collection.matches.get('code_log_matches')
    if type(scored) is not list:
        return False
    seen = set()
    for row in scored:
        if (type(row) is not dict or row.get('kind') != 'log_statement'
                or type(row.get('id')) is not int or row['id'] not in members or row['id'] in seen
                or scored_schema_rejections(row) or row.get('query_risk_flags')
                or event_match(row, query)['priority'] > 0 or independently_named_log_owner(row, query)):
            return False
        seen.add(row['id'])
        original = members[row['id']]
        if any(type(row.get(k)) is not type(original.get(k)) or row.get(k) != original.get(k) for k in IDENTITY):
            return False
    for row in raw['query_handoff']['log_anchors']:
        if (type(row) is not dict or set(row) - RAW_KEYS or row.get('effect_id') is not None
                or row.get('evidence_class') != 'direct' or row.get('log_id') not in members):
            return False
        original = members[row['log_id']]
        if any(row.get(k) != original.get(k) for k in ('file_path', 'function', 'line', 'logger', 'message_template')):
            return False
    return True
