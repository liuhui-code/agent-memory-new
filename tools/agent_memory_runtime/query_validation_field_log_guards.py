# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Complete hidden/visible log guards; an empty rejection list is not authority."""
from .query_validation_log_capture import (
    bounded_metadata, validation_logs, validation_log_inventory)
from .query_validation_field_request import validation_field_request
from .log_event_identity import event_match
from .query_log_owner_admission import independently_named_log_owner
from .query_record_loop_selection import protected_record_loop

FLAGS = ('identity_match', 'log_identity_match', 'graph_neighbor', 'graph_relation')
IDENTITY = ('id','project_id','file_path','function','line','logger','level','message_template',
            'source_digest','index_generation')


ORDINARY_REASONS = frozenset('business_terms symptom_terms likely_causes business_summary business_event trigger_stage process_hint neighbor_terms log_message log_context search_terms query_focus_coverage multi_concept_coverage static_wrapped'.split())
PROTECTED_REASONS = frozenset('exact_function exact_file_path exact_identifier exact_symbol exact_log_message exact_business_event graph_neighbor graph_relation identity_match log_identity_match'.split())
SCORED_KEYS = frozenset('business_event business_summary business_terms call_path call_path_locations end_line evidence_class file_path function id index_generation kind level line likely_causes log_signal_band log_signal_score logger match_reasons message_template missing_signals neighbor_terms observability_gaps present_signals process_hint project_id query_risk_flags raw_call raw_statement recall_fusion recall_lanes retrieval_explanation score search_terms sink_log_id source_digest start_line suggested_log_fields symptom_terms trigger_stage truncated trust_cap trust_cap_reasons trust_level trust_reasons trust_score updated_at wrapper_depth wrapper_symbol'.split()) | frozenset(FLAGS)
RAW_KEYS = frozenset('business_event call_path call_path_locations effect_id evidence_class file_path function line log_id logger message_template process_hint symptom_terms trigger_stage truncated wrapper_depth wrapper_symbol level'.split()) | frozenset(FLAGS)


def scored_schema_rejections(row):
    if type(row) is not dict or not bounded_metadata(row):return ['invalid-scored-shape']
    if set(row)-SCORED_KEYS:return ['unknown-scored-key']
    rs=row.get('match_reasons')
    if type(rs) is not list or any(type(v) is not str for v in rs):return ['invalid-scored-reasons']
    reasons=[]
    for value in rs:
        if value in PROTECTED_REASONS:reasons.append('protected-scored-reason:'+value)
        elif value in ORDINARY_REASONS:pass
        elif value.startswith('expanded_query:') and value.partition(':')[2] in ORDINARY_REASONS:pass
        else:reasons.append('unknown-scored-reason:'+value)
    if any(row.get(k) for k in FLAGS):reasons.append('protected-scored-flag')
    return reasons


def complete_candidate_rejections(project, query, collection, capture, raw, pool, *, pending=False):
    # Authenticate complete immutable inventory and current sealed scored state.
    if validation_field_request(query) is None:
        return ['invalid-request']
    if validation_logs(project, query, collection) is not capture:
        return ['invalid-capture']
    inventory = validation_log_inventory(project, capture)
    if inventory is None or inventory['query'] != query:
        return ['invalid-inventory']
    scored = collection.matches.get('code_log_matches')
    if type(scored) is not list or not bounded_metadata([raw,pool,scored]):
        return ['invalid-bounded-shape']
    reasons=[]
    anchors=raw.get('query_handoff',{}).get('log_anchors')
    if type(anchors) is not list:return ['invalid-raw-log-schema']
    if any(type(r) is not dict or set(r)-RAW_KEYS for r in anchors):return ['unknown-raw-log-key']
    # Preserve original code/path/visible protection even when another layer
    # also rejects. Never claim hidden-only first loss from this combined check.
    if protected_record_loop(raw, query, pool, pending=pending):
        reasons.append('existing-baseline-protection')
    members={}
    for lane in ('direct','effects'):
        for row in inventory[lane]:
            key=(lane,row['id']); members[key]=row
            label=lane+':'+str(row['id'])
            if event_match(row,query)['priority']>0:
                reasons.append(label+':complete-event')
            if independently_named_log_owner(row,query):
                reasons.append(label+':complete-path-or-qualified-owner')
            if any(row.get(k) for k in FLAGS):
                reasons.append(label+':complete-identity-flag')
            if lane=='effects':
                locations=row.get('call_path_locations')
                if type(locations) is not list:
                    return ['invalid-complete-effect-paths']
                for location in locations:
                    if type(location) is not str or location.count('#')!=1:
                        return ['invalid-complete-effect-location']
                    path,function=location.split('#')
                    # These written locations still need the separate complete
                    # typed-edge/source verifier. This loop grants no proof.
                    if independently_named_log_owner({'file_path':path,'function':function},query):
                        reasons.append(label+':complete-effect-dependency-owner')

    seen=set()
    for row in scored:
        if type(row) is not dict:
            return ['invalid-scored-row']
        kind=row.get('kind')
        lane='effects' if kind=='log_effect' else 'direct' if kind=='log_statement' else None
        ident=row.get('id')
        if lane is None or type(ident) is not int:
            return ['invalid-scored-namespace']
        key=(lane,ident)
        if key not in members or key in seen:
            return ['uncovered-scored-row']
        seen.add(key); original=members[key]
        # Scoring may enrich nonidentity fields, never replace the source tuple.
        if any(type(row.get(k)) is not type(original.get(k)) or row.get(k)!=original.get(k)
               for k in IDENTITY):
            return ['scored-identity-drift']
        reasons.extend(lane+':'+str(ident)+':'+r for r in scored_schema_rejections(row))
        flags=row.get('match_reasons')
        if type(flags) is not list or any(type(x) is not str for x in flags):
            return ['invalid-scored-reasons']
        label=lane+':'+str(ident)
        if independently_named_log_owner(row,query):
            reasons.append(label+':sealed-scored-owner')
        if event_match(row,query)['priority']>0:
            reasons.append(label+':sealed-scored-event')
        if any(row.get(k) for k in FLAGS):
            reasons.append(label+':sealed-scored-identity-flag')
    # No equality requirement with original lanes: zero-score rows may have no
    # scored projection. They were still checked above, never declared safe due
    # to absent reasons. Check identity again after inspecting current state.
    if validation_logs(project,query,collection) is not capture:
        return ['capture-changed-during-check']
    return reasons
