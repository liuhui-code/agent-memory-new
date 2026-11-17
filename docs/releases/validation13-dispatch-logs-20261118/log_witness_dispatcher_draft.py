# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Unexecuted concrete component dispatcher. Never interprets unavailable as pass.

Run only after independent fixture/API/control freeze. No CLI/full suite.
Unsupported prospective cases raise NotImplementedError and BLOCK completeness.
"""
import copy
import importlib.util
import json
from pathlib import Path
import sqlite3

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('validation_log_fixture_draft', HERE/'validation_log_fixture_draft.py')
# Normal import, rather than speculative execution of a fixture at module load.
import sys
sys.path.insert(0, str(HERE))
from validation_log_fixture_draft import build_fixture, candidate_api


def _logs(f):
    return f.raw['query_handoff']['log_anchors']


def _replace_row(row, **changes):
    result = dict(row); result.update(changes); return result


def _db_change(f, table, changes):
    from tools.agent_memory_runtime.storage import connect
    with connect(f.project) as db:
        for column, value in changes.items():
            assert column in {r['name'] for r in db.execute('PRAGMA table_info('+table+')')}
            db.execute('UPDATE '+table+' SET '+column+'=? WHERE project_id=?', (value,f.project.project_id))
        db.commit()


# These are deliberately not fake passing variants. They require additional
# genuine source/collector construction or integrated new binder before freeze.
PENDING = {
 'direct-complete':'actual direct-only collector fixture',
 'hidden-benign':'authentic extra hidden candidate source/DB fixture',
 'id-namespace':'genuine namespace-collision fixture if actual IDs differ',
 'direct-crop':'complete hidden candidate fixture',
 'hidden-event':'protected original request plus authentic full collection',
 'hidden-owner':'protected original request plus authentic full collection',
 'hidden-path':'protected original request plus authentic full collection',
 'hidden-effect-event':'protected original request plus authentic full collection',
 'wrong-sink':'second authentic sink source/row fixture',
 'candidate-overflow':'65 genuinely distinct source-backed rows',
 'noncode-change':'new integrated binder/compact transaction assertion',
 'over-output-budget':'exact sourceview plus integrated budget fixture',
 'raw-full-compact-omitted-empty':'new integrated binder/render assertion',
 'renderer-reorder':'new integrated binder/render assertion',
 'compact-filled-empty':'new integrated compact baseline rejection assertion',
 'compact-wrong-order':'new integrated compact baseline rejection assertion',
 'compact-field-tamper':'new integrated compact baseline rejection assertion',
 'bounded-read-dedup':'new resolver instrumentation seam',
 'huge-audit-small-logs':'new integrated binding precheck instrumentation',
 'huge-pool-small-logs':'new integrated binding precheck instrumentation',
 'mutated-binding-input':'new integrated receipt precheck instrumentation',
}


INTEGRATED = {'noncode-change','over-output-budget','raw-full-compact-omitted-empty',
 'renderer-reorder','compact-filled-empty','compact-wrong-order','compact-field-tamper',
 'huge-audit-small-logs','huge-pool-small-logs','mutated-binding-input','bounded-read-dedup'}
for _name in INTEGRATED | {'direct-complete','hidden-benign','id-namespace','direct-crop','wrong-sink','candidate-overflow'}:
    PENDING.pop(_name, None)


def _integrated(case_id, f, capture):
    from tools.agent_memory_runtime import query_validation_field_selection as selection
    from tools.agent_memory_runtime.query_output_loop_selection import snapshot
    from tools.agent_memory_runtime.context_record_loop_transaction import restore_whitelist
    from unittest.mock import patch
    raw=copy.deepcopy(f.raw); pool=copy.deepcopy(f.pool)
    if case_id=='over-output-budget': raw['output_budget']['target_tokens']=1
    if case_id=='huge-audit-small-logs':
        raw['query_audit']['oversize_probe']='x'*(1048576+1)
    if case_id=='huge-pool-small-logs': pool=pool*17000
    capture(f.project,f.query,f.capture_calls[0][2],f.collection,f.direct,f.effects)
    if case_id in ('huge-audit-small-logs','huge-pool-small-logs'):
        # These whole inputs must be rejected before existing recursive copies.
        with patch.object(selection,'deepcopy',side_effect=AssertionError('unbounded copy reached')), \
             patch.object(selection,'snapshot',side_effect=AssertionError('unbounded snapshot reached')):
            bound=selection.bind_validation_field_context(f.project,f.query,raw,pool,f.collection)
        assert bound is raw
        return {'id':case_id,'asserted':'precopy finite rejection'}
    bound=selection.bind_validation_field_context(f.project,f.query,raw,pool,f.collection)
    assert type(bound) is selection.ValidationContext, 'actual new nonempty binder not issued'
    assert selection.validation_field_receipt(bound) is not None
    from tools.agent_memory_runtime.context_compact import _compact_context
    baseline=_compact_context(dict(bound))
    if case_id=='mutated-binding-input':
        cycle=[]; cycle.append(cycle)
        f.collection.recall_audit['cycle_probe']=cycle
        with patch.object(selection,'snapshot',side_effect=AssertionError('unsafe resnapshot reached')):
            assert selection.validation_field_receipt(bound) is None
        return {'id':case_id,'asserted':'receipt precheck before recursive snapshot'}
    if case_id=='bounded-read-dedup':
        # Freeze this resolver seam explicitly; absence is never success.
        from tools.agent_memory_runtime import query_validation_log_provenance as provenance
        reader=getattr(provenance,'read_source_bytes',None)
        if reader is None: raise NotImplementedError('reviewed read_source_bytes(project,path,limit) seam absent')
        runs=[]
        for _ in range(2):
            with patch.object(provenance,'read_source_bytes',wraps=reader) as spy:
                assert selection.validation_field_receipt(bound) is not None
                paths=[str(call.args[1]) for call in spy.call_args_list]
                assert paths and len(paths)==len(set(paths)) and len(paths)<=12
                assert all(call.args[2]==2097153 for call in spy.call_args_list)
                runs.append(paths)
        assert runs[0]==runs[1], 'fresh repeated check must not reuse stale cache'
        return {'id':case_id,'asserted':'bounded per-verification source reads','reads':runs}
    if case_id in ('raw-full-compact-omitted-empty','renderer-reorder'):
        rawlogs=bound['query_handoff']['log_anchors']; logs=baseline['query_handoff']['log_anchors']
        direct=next(x for x in logs if x.get('effect_id') is None)
        assert 'call_path' not in direct and 'call_path_locations' not in direct
        def keys(xs):return [('effect',x['effect_id']) if x.get('effect_id') is not None else ('direct',x['log_id']) for x in xs]
        assert keys(rawlogs)!=keys(logs) and set(keys(rawlogs))==set(keys(logs))
        result=selection.compact_validation_field(bound,baseline)
        assert result is not baseline, 'valid fixed main must actually apply source view'
        assert restore_whitelist(result,baseline)==baseline
        assert result['query_handoff']['log_anchors']==logs
        return {'id':case_id,'asserted':'real renderer projection and unchanged noncode'}
    if case_id=='over-output-budget':
        assert selection.compact_validation_field(bound,baseline) is baseline
        return {'id':case_id,'asserted':'valid proof budget fallback'}
    bad=copy.deepcopy(baseline)
    if case_id=='compact-filled-empty':
        direct=next(x for x in bad['query_handoff']['log_anchors'] if x.get('effect_id') is None)
        direct['call_path']=[]; direct['call_path_locations']=[]
    elif case_id=='compact-wrong-order': bad['query_handoff']['log_anchors'].reverse()
    elif case_id in ('noncode-change','compact-field-tamper'):
        bad['query_handoff']['path_context']={'unexpected_projection':'changed'}
    else: raise AssertionError('unhandled integrated control '+case_id)
    assert bad!=baseline
    assert selection.compact_validation_field(bound,bad) is bad
    return {'id':case_id,'asserted':'caller renderer-baseline tamper rejection'}


def run_case(case_id, fresh_folder):
    """Return evidence only after real assertion; no skip/catch-to-pass."""
    document=json.loads((HERE/'LOG-WITNESS-CONTROLS-DRAFT.json').read_text())
    controls=document['controls']+document.get('supplemental_boundary_controls',[])+document.get('supplemental_binding_controls',[])
    by_id={c['id']:c for c in controls}
    if case_id not in by_id: raise AssertionError('unknown fixed control '+case_id)
    if case_id in PENDING: raise NotImplementedError(case_id+': '+PENDING[case_id])
    # Missing production API is NOT_IMPLEMENTED, not a semantic before failure.
    capture,get,verify=candidate_api()
    variant={'no-log-preserved':'empty','direct-complete':'direct','hidden-benign':'hidden',
             'direct-crop':'hidden','wrong-sink':'hidden','candidate-overflow':'boundary65'}.get(case_id,'logged')
    f=build_fixture(fresh_folder,variant)
    if case_id in INTEGRATED:
        return _integrated(case_id,f,capture)
    if case_id in ('no-log-preserved','no-issued-old-API'):
        from tools.agent_memory_runtime.query_validation_no_logs import validation_no_logs
        value=validation_no_logs(f.project,f.query,f.collection)
        assert (value is not None)==(case_id=='no-log-preserved')
        return {'id':case_id,'asserted':'unchanged absence API'}
    retrieval=f.capture_calls[0][2]
    direct=list(f.direct); effects=copy.deepcopy(f.effects)
    if case_id=='effect-inferred':
        f.mutate_db('code_log_effects',effects[0]['id'],evidence_class='inferred_wrapped')
        effects[0]['evidence_class']='inferred_wrapped'
    elif case_id=='unsupported-effect':
        f.mutate_db('code_log_effects',effects[0]['id'],wrapper_depth=2)
        effects[0]['wrapper_depth']=2
    elif case_id=='duplicate': direct.append(direct[0])
    elif case_id=='lane-move': effects.append(dict(direct.pop(0)))
    elif case_id=='custom-mapping':
        class Custom(dict): pass
        direct[0]=Custom(dict(direct[0]))
    elif case_id=='oversize-row-shape':
        # A genuine sqlite Row exceeding columns; no arbitrary Mapping adapter.
        db=sqlite3.connect(':memory:'); db.row_factory=sqlite3.Row
        direct[0]=db.execute('SELECT '+','.join('0 AS k'+str(i) for i in range(129))).fetchone(); db.close()
    elif case_id=='unknown-proof': effects[0].pop('sink_log_id')
    if case_id=='id-namespace':
        assert {r['id'] for r in direct}&{r['id'] for r in effects}, 'fixture must actually exercise colliding namespace ids'
    if case_id=='candidate-overflow':
        assert len(direct)+len(effects)==65
        capture(f.project,f.query,retrieval,f.collection,direct,effects)
        assert get(f.project,f.query,f.collection) is None
        return {'id':case_id,'asserted':'actual 65-candidate capture ceiling'}
    capture(f.project,f.query,retrieval,f.collection,direct,effects)
    receipt=get(f.project,f.query,f.collection)
    raw_logs=copy.deepcopy(_logs(f)); scope=list(f.source_paths)
    isolation_before=verify(f.project,receipt,raw_logs,scope) if case_id in ('effect-crop','direct-crop','mutate-row') else None
    if case_id in ('effect-crop','direct-crop','mutate-row'): assert isolation_before is not None
    if case_id=='unissued': receipt={}
    elif case_id=='collection-swap' or case_id=='cross-pass':
        other=copy.copy(f.collection)
        assert other is not f.collection
        receipt=get(f.project,f.query,other)
    elif case_id=='cross-query': receipt=get(f.project,f.query+' x',f.collection)
    elif case_id=='cross-project':
        other=build_fixture(Path(fresh_folder).parent/(Path(fresh_folder).name+'-other'),'logged')
        receipt=get(other.project,f.query,f.collection)
    elif case_id=='recapture': capture(f.project,f.query,retrieval,f.collection,direct,effects)
    elif case_id=='effect-crop': effects.clear()
    elif case_id=='direct-crop':
        visible={r.get('log_id') for r in raw_logs if r.get('effect_id') is None}
        hidden=next(r for r in direct if r['id'] not in visible); direct.remove(hidden)
    elif case_id=='wrong-sink':
        other=next(r for r in direct if r['id']!=effects[0]['sink_log_id'])
        f.mutate_db('code_log_effects',effects[0]['id'],sink_log_id=other['id'])
    elif case_id=='mutate-row': effects[0]['message_template']+=' changed'
    elif case_id=='mutate-visible' or case_id=='raw-mutation-after-issue': raw_logs[0]['message_template']+=' changed'
    elif case_id=='unknown-visible': raw_logs[0]['log_id']=999999
    elif case_id=='duplicate-visible': raw_logs.append(copy.deepcopy(raw_logs[0]))
    elif case_id=='effect-as-direct':
        row=next(r for r in raw_logs if r.get('effect_id') is not None)
        row.pop('effect_id'); row['evidence_class']='direct'
    elif case_id=='stale-source':
        path=Path(f.project.root)/direct[0]['file_path'];path.write_bytes(path.read_bytes()+b'\n// changed\n')
    elif case_id=='stale-db': _db_change(f,'code_index_state',{'generation':999})
    elif case_id=='stale-edge':
        edge=next(r for r in f.database_rows['memory_edges'] if r['relation']=='calls' and r['valid_to'] is None)
        f.mutate_db('memory_edges',edge['id'],valid_to='2026-11-17T00:00:00Z')
    elif case_id=='outside-scope': scope.remove(direct[0]['file_path'])
    elif case_id=='unknown-path': scope.append('../outside.ts')
    elif case_id=='oversize-source': (Path(f.project.root)/direct[0]['file_path']).write_bytes(b'x'*(2097152+1))
    eligible=case_id in ('effect-crop','direct-crop','mutate-row','direct-complete','hidden-benign','id-namespace','effect-static','actual-sqlite-row','repeat-validation-idempotent')
    iterations=9 if case_id=='repeat-validation-idempotent' else 1
    for _ in range(iterations):
        value=verify(f.project,receipt,raw_logs,scope)
        assert (value is not None)==eligible, (case_id,'unexpected proof eligibility')
        if isolation_before is not None: assert value==isolation_before, 'local copy altered complete immutable proof'
    return {'id':case_id,'asserted':'real private proof eligibility','iterations':iterations}


def coverage():
    """Static transparency only, not test result; pending entries block freeze."""
    doc=json.loads((HERE/'LOG-WITNESS-CONTROLS-DRAFT.json').read_text())
    cases=doc['controls']+doc.get('supplemental_boundary_controls',[])+doc.get('supplemental_binding_controls',[])
    return {'total':len(cases),'pending':dict(PENDING),'not_executed':True}


PRIMITIVE_CASES = {
 'primitive-cycle': False, 'primitive-depth12': True, 'primitive-depth13': False,
 'primitive-nodes16384': True, 'primitive-nodes16385': False,
 'primitive-int64': True, 'primitive-int65': False,
 'primitive-bytes1048576': True, 'primitive-bytes1048577': False,
 'primitive-scalar16384': True, 'primitive-scalar16385': False,
 'primitive-custom-dict': False, 'primitive-nan': False,
}

def run_primitive(case_id):
    # New primitive API unavailable => NOT_IMPLEMENTED, never false red/pass.
    try:
        from tools.agent_memory_runtime.query_validation_log_capture import bounded_metadata
    except ImportError as error:
        raise NotImplementedError('bounded_metadata(value)->bool missing') from error
    if case_id not in PRIMITIVE_CASES: raise AssertionError('unregistered primitive')
    if case_id=='primitive-cycle': value=[]; value.append(value)
    elif case_id.startswith('primitive-depth'):
        value=None
        for _ in range(int(case_id.removeprefix('primitive-depth'))): value=[value]
    elif case_id.startswith('primitive-nodes'):
        value=[None]*(int(case_id.removeprefix('primitive-nodes'))-1)
    elif case_id.startswith('primitive-int'):
        value=1<<(int(case_id.removeprefix('primitive-int'))-1)
    elif case_id.startswith('primitive-bytes'):
        value=['x'*16384]*64
        if case_id.endswith('1048577'):value.append('x')
    elif case_id.startswith('primitive-scalar'):
        value='x'*int(case_id.removeprefix('primitive-scalar'))
    elif case_id=='primitive-custom-dict':
        class Custom(dict): pass
        value=Custom()
    elif case_id=='primitive-nan': value=float('nan')
    else: raise AssertionError('missing generator')
    actual=bounded_metadata(value)
    assert type(actual) is bool and actual is PRIMITIVE_CASES[case_id]
    return {'id':case_id,'asserted':'exact primitive boundary','result':actual}


def run_reader_limit(fresh_folder):
    # Reader-only bounded IO assertion; no digest/provenance check can mask it.
    try:
        from tools.agent_memory_runtime.query_validation_log_provenance import read_source_bytes
    except ImportError as error:
        raise NotImplementedError('read_source_bytes missing') from error
    f=build_fixture(fresh_folder,'logged')
    path=f.source_paths[0]; target=Path(f.project.root)/path
    target.write_bytes(b'x'*(2097152+100))
    result=read_source_bytes(f.project,path,2097153)
    assert type(result) is bytes and len(result)==2097153
    # This is an oversize sentinel, not accepted proof. Verifier must reject it.
    target.write_bytes(b'x'*2097152)
    result=read_source_bytes(f.project,path,2097153)
    assert type(result) is bytes and len(result)==2097152
    return {'id':'reader-limit-direct','asserted':'bounded raw bytes and oversize sentinel independent of digest'}
