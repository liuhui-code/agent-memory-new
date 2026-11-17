"""Pure admitted-scope entity declaration join; no I/O or output-root authority."""
from pathlib import PurePosixPath

from .sql_slot_source import classify_sql_owner, classify_ui_owner, inventory_source
from .sql_slot_source_inventory import authenticated, Unknown


def _target(path, binding, paths, typename):
    if (type(binding) is not dict or binding.get('local') != typename
            or binding.get('imported') != typename):
        raise Unknown('entity_import_alias_or_name')
    module = binding.get('module')
    if (type(module) is not str or not module.startswith('.') or '\\' in module
            or type(path) is not str or path not in paths):
        raise Unknown('entity_import_module')
    parts = list(PurePosixPath(path).parent.parts)
    for part in module.split('/'):
        if part in ('', '.'):
            continue
        if part == '..':
            if not parts:
                raise Unknown('entity_import_escape')
            parts.pop()
        else:
            parts.append(part)
    name = '/'.join(parts)
    found = [p for p in paths if p == name or p == name + '.ets']
    if len(found) != 1:
        raise Unknown('entity_not_in_original_scope_or_ambiguous')
    return found[0]


def _owner(path, name, inventories, sources):
    found = [o for o in inventories[path]['declarations'] if o.get('name') == name]
    if len(found) != 1:
        raise Unknown('owner_missing_or_ambiguous')
    authenticated(sources[path], found[0])
    return found[0]


def entity_join(sql_path, match, ui_path, chain, inventories, sources):
    """Authenticate common named entity and public string field inside given maps.

    Returned declarations are source evidence only. The caller authenticates DB
    owner metadata and retains all scope digests; no entity becomes an output root.
    """
    try:
        if (type(inventories) is not dict or type(sources) is not dict
                or set(inventories) != set(sources) or sql_path not in sources
                or ui_path not in sources or type(match) is not dict or type(chain) is not dict):
            raise Unknown('scope_or_match_shape')
        # Complete source inventories remain mandatory even for non-output paths.
        for path, source in sources.items():
            given = inventories[path]
            if type(source) is not str or type(given) is not dict or given.get('status') != 'known':
                raise Unknown('scope_inventory_unknown')
            fresh = inventory_source(source)
            if fresh.get('status') != 'known' or fresh != given:
                raise Unknown('scope_inventory_changed')
            for declaration in given['declarations']:
                authenticated(source, declaration)
        sql_owner = _owner(sql_path, match['owner'], inventories, sources)
        ui_owner = _owner(ui_path, chain['owner'], inventories, sources)
        sql_result = classify_sql_owner(sources[sql_path], sql_owner, match['method'], 'SQL')
        ui_result = classify_ui_owner(sources[ui_path], ui_owner, chain['method'], chain['state'])
        if (sql_result['status'] != 'known' or match not in sql_result['matches']
                or ui_result['status'] != 'known' or chain not in ui_result['chains']):
            raise Unknown('source_witness_changed')
        result_type, element_type = match['result_type'], chain['element_type']
        # Legacy unannotated SQL forwarding can serve only the old string UI
        # branch. None is unknown type information, never inferred from UI/helper.
        if result_type in (None, 'string') and element_type == 'string':
            if (match['result_import'] is not None or chain['element_import'] is not None
                    or chain['render_field'] is not None or chain['member_expression_span'] is not None):
                raise Unknown('string_branch_shape')
            return dict(status='known', entity=None)
        if result_type is None or result_type == 'string' or element_type == 'string' or result_type != element_type:
            raise Unknown('mixed_or_different_element_type')
        sql_target = _target(sql_path, match['result_import'], sources, result_type)
        ui_target = _target(ui_path, chain['element_import'], sources, element_type)
        if sql_target != ui_target:
            raise Unknown('different_entity_identity')
        if (match['result_import'] not in sql_owner._imports
                or chain['element_import'] not in ui_owner._imports):
            raise Unknown('entity_import_changed')
        owner = _owner(sql_target, result_type, inventories, sources)
        if owner['kind'] != 'class' or owner['decorators'] or owner['modifiers'] != ['export']:
            raise Unknown('entity_not_exported_plain_class')
        fields = [f for f in owner['fields'] if f['name'] == chain['render_field']]
        if len(fields) != 1:
            raise Unknown('entity_field_missing_or_ambiguous')
        field = fields[0]
        if (field['type'] != 'string' or field['decorators']
                or field['modifiers'] not in ([], ['public'])):
            raise Unknown('entity_field_not_public_plain_string')
        return dict(status='known', entity=dict(
            file_path=sql_target, name=owner['name'], owner_declaration=owner, field_declaration=field,
            owner_span=owner['span'], field_span=field['span']))
    except (Unknown, KeyError, TypeError, ValueError, AttributeError, IndexError) as error:
        return dict(status='unknown', reason=str(error))
