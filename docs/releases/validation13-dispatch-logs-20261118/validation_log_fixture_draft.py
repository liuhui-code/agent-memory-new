# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Prospective synthetic component factory. Not a product CLI/before runner.

No execution before review. Real indexing/collector and original functions run;
spies only retain arguments/results and do not forge receipts or modify returns.
"""
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sqlite3
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
INPUT = Path(__file__).with_name('BEFORE-INPUT-DRAFT.json')


@dataclass
class Fixture:
    project: object
    query: str
    collection: object
    pool: list
    raw: dict
    compact: dict
    issued_raw: object
    direct: list
    effects: list
    sources: dict
    source_paths: tuple
    ids: dict
    database_rows: dict
    capture_calls: list
    writer_events: list

    def render_baseline(self):
        from tools.agent_memory_runtime.context_compact import _compact_context
        return _compact_context(deepcopy(self.raw))

    def mutate_db(self, table, row_id, **changes):
        from tools.agent_memory_runtime.storage import connect
        allowed={'code_symbols','code_log_statements','code_log_effects','memory_edges','code_files'}
        if table not in allowed or not changes:raise ValueError('mutation table/fields')
        with connect(self.project) as db:
            columns={r['name'] for r in db.execute('PRAGMA table_info('+table+')')}
            if not set(changes)<=columns:raise ValueError('unknown mutation field')
            assignments=','.join('"'+k+'"=?' for k in changes)
            cur=db.execute('UPDATE '+table+' SET '+assignments+' WHERE project_id=? AND id=?',
                           (*changes.values(),self.project.project_id,row_id))
            if cur.rowcount!=1:raise AssertionError('mutation identity not unique')
            db.commit()


def build_fixture(folder, variant='logged'):
    """Build new schema/IDs/index/edges from fixed independent source bytes.

    Never restores saved DB, captured raw JSON, or historical Project identity.
    Only the fixed source/query bytes are shared with the prospective fixture.
    """
    from tools.agent_memory_runtime.storage import resolve_project, ensure_initialized, connect
    from tools.agent_memory_runtime.code_wiki_indexing import write_wiki_index, record_learn_scope
    from tools.agent_memory_runtime.code_wiki_refresh import add_episode_from_values
    from tools.agent_memory_runtime.context_composition import build_context_facade
    from tools.agent_memory_runtime.context_compact import compact_context
    from tools.agent_memory_runtime import query_validation_no_logs as no_logs
    from tools.agent_memory_runtime import query_validation_field_selection as selection
    from tools.agent_memory_runtime.query_collect import CollectedMatches
    if variant not in ('logged', 'empty', 'hidden', 'boundary64', 'boundary65', 'direct'):
        raise ValueError('unregistered factory variant')
    inputs = json.loads(INPUT.read_text())
    wanted = 'logged-dispatch-main' if variant in ('logged','hidden') else 'empty-dispatch-control'
    world = deepcopy(next(w for w in inputs['worlds'] if w['id'] == wanted))
    count={'hidden':12,'boundary64':64,'boundary65':65,'direct':1}.get(variant,0)
    if count:
        text='export class ComponentLogBank {\n  reportAccount(): void {\n'
        text+=''.join("    console.info('Account batch item %03d')\n" % i for i in range(count))
        text+='  }\n}\n'
        world['sources']['ComponentLogBank.ts']=text
        world['source_sha256']['ComponentLogBank.ts']=hashlib.sha256(text.encode()).hexdigest()
    folder = Path(folder)
    if folder.exists():
        raise ValueError('factory requires a fresh child directory')
    source = folder / 'source'; source.mkdir(parents=True)
    for name, text in world['sources'].items():
        if hashlib.sha256(text.encode()).hexdigest() != world['source_sha256'][name]:
            raise AssertionError('frozen source drift')
        (source / name).write_bytes(text.encode())
    project = resolve_project(str(source), str(folder / 'memory'))
    ensure_initialized(project)
    files = sorted(source.glob('*.ts'))
    write_wiki_index(project, files, replace=False, skipped_by_reason={})
    record_learn_scope(project, source, 'path', 'merge', files, target_path='.')
    # Real ordinary learning episode, not injected log noise. Same low-level
    # write as learn-path; it permits realistic memory accounting controls.
    add_episode_from_values(project, 'Learn independent validation component',
                            'Indexed four independent validation sources', 'learned')
    captures = []; binds = []; writers = []
    from tools.agent_memory_runtime import query_results
    original_use=query_results.record_context_use
    original_miss=query_results.record_query_miss_if_empty

    def before_writer(name,p,data):
        destination=folder/('pre-writer-%02d-%s.sqlite3' % (len(writers),name))
        with sqlite3.connect('file:'+str(p.db_path)+'?mode=ro',uri=True) as source_db:
            with sqlite3.connect(destination) as saved_db:source_db.backup(saved_db)
        event=dict(name=name,project=p,pre_db=destination,data=deepcopy(dict(data)))
        writers.append(event)
        return event

    def observe_use(p,data):
        event=before_writer('use',p,data)
        result=original_use(p,data)
        event['completed']=True
        return result

    def observe_miss(p,kind,query,data):
        event=before_writer('miss',p,data)
        event.update(source=kind,query=query)
        result=original_miss(p,kind,query,data)
        event['completed']=True
        return result
    original_capture = no_logs.capture_validation_no_logs
    original_bind = selection.bind_validation_field_context

    def observe_capture(p, query, retrieval, collection, direct, effects):
        captures.append((p, query, retrieval, collection, list(direct), deepcopy(effects)))
        return original_capture(p, query, retrieval, collection, direct, effects)

    def observe_bind(p, query, data, items, collection=None):
        binds.append((collection, deepcopy(items)))
        return original_bind(p, query, data, items, collection)

    with patch.object(no_logs, 'capture_validation_no_logs', side_effect=observe_capture), \
         patch.object(selection, 'bind_validation_field_context', side_effect=observe_bind), \
         patch.object(query_results, 'record_context_use', side_effect=observe_use), \
         patch.object(query_results, 'record_query_miss_if_empty', side_effect=observe_miss):
        issued_raw = build_context_facade(project).execute(world['query'])
    if len(captures) != 1 or len(binds) != 1:
        raise AssertionError('unexpected actual component pass count')
    p, query, retrieval, collection, direct, effects = captures[0]
    if type(collection) is not CollectedMatches or binds[0][0] is not collection:
        raise AssertionError('not actual same-pass collector')
    if any(type(r) is not sqlite3.Row for r in direct):
        raise AssertionError('direct lane must retain actual sqlite3.Row')
    if any(type(r) is not dict for r in effects):
        raise AssertionError('effect lane must retain actual builtin dict')
    with connect(project) as db:
        names = ('code_files', 'code_symbols', 'code_log_statements', 'code_log_effects',
                 'memory_edges', 'code_index_state', 'graph_runtime_state')
        tables = {n: [dict(r) for r in db.execute('SELECT * FROM '+n+' WHERE project_id=?',
                                                (project.project_id,))] for n in names}
    ids = {}
    for row in tables['code_symbols']:
        ids[(row['file_path'], row['qualified_name'])] = row['id']
    raw = deepcopy(dict(issued_raw))
    fixture = Fixture(project, query, collection, binds[0][1], raw,
                      compact_context(dict(raw)), issued_raw, direct, effects,
                      deepcopy(world['sources']), tuple(sorted(world['sources'])), ids,
                      tables, captures, writers)
    assert_fixture(fixture, variant)
    return fixture


def assert_fixture(fixture, variant):
    """Expected genuine metadata baseline, not assertion of unimplemented API."""
    rows = fixture.database_rows
    assert {r['file_path'] for r in rows['code_files']} == set(fixture.source_paths)
    assert len(rows['code_index_state']) == len(rows['graph_runtime_state']) == 1
    for row in rows['code_files']:
        assert row['source_digest'] == hashlib.sha256(fixture.sources[row['file_path']].encode()).hexdigest()
    for path, owner, method in [('AccountDraftPanel.ts', 'AccountDraftPanel', 'submitDraft'),
                                ('MemberDraftPanel.ts', 'MemberDraftPanel', 'submitAccount')]:
        methods = [r for r in rows['code_symbols'] if r['file_path']==path and
                   r['owner_name']==owner and r['symbol']==method]
        assert len(methods)==1 and (methods[0]['start_line'], methods[0]['end_line'])==(3,9)
        if variant in ('logged','empty'):
            assert any(r['kind']=='symbol' and r['id']==methods[0]['id'] and r['file_path']==path
                       for r in fixture.pool), 'actual original pool missing method'
    if variant in ('boundary64','boundary65','direct'):
        count={'boundary64':64,'boundary65':65,'direct':1}[variant]
        assert len(fixture.direct)==count and not fixture.effects
        assert len({r['id'] for r in fixture.direct})==count
        assert len({(r['file_path'],r['line']) for r in fixture.direct})==count
        assert all(r['file_path']=='ComponentLogBank.ts' for r in fixture.direct)
        return
    if variant=='hidden':
        assert len(fixture.direct)==13 and len(fixture.effects)==1
        visible=fixture.raw['query_handoff']['log_anchors']
        direct_ids={a['log_id'] for a in visible if a.get('effect_id') is None}
        assert {r['id'] for r in fixture.direct}-direct_ids, 'no actually hidden direct candidate'
        return
    if variant=='empty':
        assert not fixture.direct and not fixture.effects
        return
    assert len(fixture.direct)==1 and len(fixture.effects)==1
    direct=fixture.direct[0]; effect=fixture.effects[0]
    assert direct['file_path']=='AccountDraftPanel.ts' and direct['function']=='dispatchDraft'
    assert direct['message_template']=='Account draft dispatched'
    assert effect['wrapper_depth']==1 and effect['evidence_class']=='static_wrapped'
    assert effect['sink_log_id']==direct['id'] and effect['truncated']==0
    caller=fixture.ids['AccountDraftPanel.ts','AccountDraftPanel.submitDraft']
    sink=fixture.ids['AccountDraftPanel.ts','AccountDraftPanel.dispatchDraft']
    def edge(relation, target_type, a, b):
        found=[r for r in rows['memory_edges'] if r['source_type']=='code_symbol' and
               r['source_id']==a and r['relation']==relation and r['target_type']==target_type
               and r['target_id']==b and r['valid_to'] is None]
        assert len(found)==1
        return found[0]
    calls=edge('calls','code_symbol',caller,sink)
    emits=edge('emits_log','code_log_statement',sink,direct['id'])
    assert calls['evidence_kind']=='static_semantic_calls'
    assert emits['evidence_kind']=='code_observability'


def candidate_api():
    """Adapter seam: absence is NOT_IMPLEMENTED, never counted semantic red."""
    try:
        from tools.agent_memory_runtime.query_validation_log_capture import (
            capture_validation_logs, validation_logs)
        from tools.agent_memory_runtime.query_validation_log_provenance import verify_validation_logs
    except ImportError as error:
        raise NotImplementedError('prospective validation witness API not implemented') from error
    return capture_validation_logs, validation_logs, verify_validation_logs


# Draft adapter alias. Resource variants are capture-only, not source eligibility.
make_fixture = build_fixture
