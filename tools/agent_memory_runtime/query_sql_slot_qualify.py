"""Join finite source slots to already-admitted methods, without ranking."""
from pathlib import PurePosixPath
from .sql_slot_source import inventory_source, classify_sql_owner, classify_ui_owner
from .query_sql_slot_snapshot import load_scope, owner_row, method_root
from .context_record_loop_transaction import valid_anchors


def import_path(path, module, paths):
    if not isinstance(module, str) or not module.startswith('.') or '\\' in module:
        return None
    parts = list(PurePosixPath(path).parent.parts)
    for part in module.split('/'):
        if part in ('', '.'):
            continue
        if part == '..':
            if not parts: return None
            parts.pop()
        else: parts.append(part)
    name = '/'.join(parts)
    candidates = [p for p in paths if p == name or p == name + '.ets']
    return candidates[0] if len(candidates) == 1 else None


def anchor(source, row):
    lo, hi = row['start_line'], row['end_line']
    span = dict(symbol=row['symbol'], start_line=lo, end_line=hi)
    return dict(file_path=row['file_path'], symbol=row['symbol'], symbol_type=row['symbol_type'],
                record_ids=[row['id']], record_type='code_symbol', source_ranges=[span],
                read_window=dict(start_line=lo, end_line=hi), role='primary', source_excerpts=[dict(
                    span, content='\n'.join(source.splitlines()[lo-1:hi]),
                    source='validated_request_snapshot', selection_reason='complete_sql_state_render_method',
                    focus_line=None, truncated=False)])


def state_metadata(scope, path, inventory):
    """Missing state index is allowed; an existing contradictory index is not."""
    expected = {}
    for owner in inventory['declarations']:
        for field in owner['fields']:
            if any(d['name'] in {'State', 'Local'} for d in field['decorators']):
                expected[owner['name'] + '.' + field['name']] = (owner, field)
    field_names = {field['name'] for _, field in expected.values()}
    seen = set()
    for row in scope['rows']:
        if row['file_path'] != path: continue
        qname = row['qualified_name']
        if row['symbol_type'] != 'state' and qname not in expected and row['symbol'] not in field_names: continue
        if qname not in expected or qname in seen: return False
        owner, field = expected[qname]; seen.add(qname)
        if (row['symbol_type'] != 'state' or row['symbol'] != field['name']
                or row['owner_name'] not in ('', None, owner['name'])
                or row['owner_kind'] not in ('', None, 'component')
                or (row['start_line'], row['end_line']) !=
                (field['span']['start_line'], field['span']['end_line'])):
            return False
    return True


def entity_metadata(scope, evidence):
    """Authenticate a non-output entity container; never promote its fields."""
    if evidence is None: return True
    path = evidence['file_path']
    owner = owner_row(scope, path, evidence['owner_declaration'])
    if owner is None or owner['symbol_type'] != 'class': return False
    field = evidence['field_declaration']; bounds = field['span']
    qname = owner['symbol'] + '.' + field['name']
    candidates = [r for r in scope['rows'] if r['file_path'] == path and
                  (r['symbol'] == field['name'] or r['qualified_name'] == qname or
                   (r['start_line'], r['end_line']) == (bounds['start_line'], bounds['end_line']))]
    if len(candidates) > 1: return False
    for row in candidates:
        if (row['symbol'] != field['name'] or row['qualified_name'] != qname
                or row['symbol_type'] not in {'property', 'field'}
                or row['owner_name'] not in ('', None, owner['symbol'])
                or row['owner_kind'] not in ('', None, owner['owner_kind'])
                or (row['start_line'], row['end_line']) != (bounds['start_line'], bounds['end_line'])):
            return False
    return True


def qualify_sql_slot(project, descriptor, pool):
    scope = load_scope(project, pool)
    if scope is None: return None
    sql, ui, inventories = [], [], {}
    for path, source in scope['sources'].items():
        inventory = inventory_source(source)
        if inventory['status'] != 'known' or not state_metadata(scope, path, inventory): return None
        inventories[path] = inventory
        for declaration in inventory['declarations']:
            owner = owner_row(scope, path, declaration)
            if owner is None: return None
            sql_result = classify_sql_owner(source, declaration, descriptor['method'], descriptor['sql_kind'])
            ui_result = classify_ui_owner(source, declaration, descriptor['method'], descriptor['state'])
            if sql_result['status'] != 'known' or ui_result['status'] != 'known': return None
            for match in sql_result['matches']:
                root = method_root(scope, path, owner, match['declaration'])
                if root is None: return None
                sql.append((path, owner, match, root))
            for chain in ui_result['chains']:
                submit = method_root(scope, path, owner, chain['submit_declaration'])
                build = method_root(scope, path, owner, chain['build_declaration'])
                if submit is None or build is None: return None
                ui.append((path, owner, chain, submit, build))
    # Every positive SQL owner must be accounted for; no orphan positive is hidden.
    if not sql or not ui: return None
    used, members = set(), []
    for path, owner, chain, submit, build in ui:
        binding = chain['receiver_import']
        target = import_path(path, binding['module'], scope['paths'])
        matches = [(i, item) for i, item in enumerate(sql) if item[0] == target
                   and item[1]['symbol'] == binding['imported']]
        if len(matches) != 1: return None
        index, item = matches[0]
        from .sql_slot_entity_join import entity_join
        joined = entity_join(item[0], item[2], path, chain, inventories, scope['sources'])
        if joined['status'] != 'known' or not entity_metadata(scope, joined.get('entity')): return None
        if descriptor['excluded_owner'] in {owner['symbol'], item[1]['symbol']}:
            return None
        used.add(index)
        members.extend([item[3], submit, build])
    if used != set(range(len(sql))): return None
    unique = {}
    for member in members:
        unique[(member['file_path'], member['id'])] = member
    members = list(unique.values())
    anchors = [anchor(scope['sources'][r['file_path']], r) for r in members]
    if not valid_anchors(anchors): return None
    return dict(scope=scope, members=members, anchors=anchors)
