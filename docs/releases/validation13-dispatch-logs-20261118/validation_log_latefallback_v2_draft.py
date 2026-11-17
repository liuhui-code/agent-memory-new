# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Unexecuted V2 actual-handler mutation controls; no receipt/return fabrication."""
import argparse
from contextlib import redirect_stdout
from copy import deepcopy
from dataclasses import replace
import importlib.util
import io
import json
from pathlib import Path
import sqlite3
import sys
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
STAMP='2026-11-17T00:00:00+00:00'
STAGES=('before_enrich','before_accounting','before_terminal_compact')


def backup(project,path):
    with sqlite3.connect('file:'+str(project.db_path)+'?mode=ro',uri=True) as source:
        with sqlite3.connect(path) as dest:source.backup(dest)


def tables(path):
    with sqlite3.connect('file:'+str(path)+'?mode=ro&immutable=1',uri=True) as db:
        db.row_factory=sqlite3.Row
        return {t:[dict(r) for r in db.execute('SELECT * FROM '+t+' ORDER BY id')]
                for t in ('semantic_facts','reflections','episodes','query_misses')}


def _run_case(stage,root,records,stdout):
    """One new logged factory and ONE actual context handler per named stage.

    Factory itself has its documented one facade setup call. In addition, two
    isolated twins each receive one actual use/miss pair for duplicate-ID proof.
    Missing serving integration is NOT_IMPLEMENTED, never semantic red/pass.
    """
    if stage not in STAGES:raise ValueError('unregistered stage')
    from tools.agent_memory_runtime import query_results as writers
    from tools.agent_memory_runtime import query_validation_field_selection as selection
    from tools.agent_memory_runtime import command_handlers as handler
    from tools.agent_memory_runtime.query_validation_log_capture import validation_logs
    from tools.agent_memory_runtime.context_source_excerpt import redact_source_excerpt_bodies
    from tools.agent_memory_runtime import usage_samples as usage_writers
    spec=importlib.util.spec_from_file_location('late_v2_factory',HERE/'validation_log_fixture_draft.py')
    factory=importlib.util.module_from_spec(spec);sys.modules[spec.name]=factory;spec.loader.exec_module(factory)
    f=factory.build_fixture(root/'fixture','logged')
    # Capability gate before scheduling the actual handler. Do not fake wiring.
    if not isinstance(f.issued_raw,selection.ValidationContext):
        raise NotImplementedError('real nonempty ValidationContext serving integration absent')
    if validation_logs(f.project,f.query,f.collection) is None:
        raise NotImplementedError('actual collector nonempty capture wiring absent')
    # Pre-existing same-query miss is a real writer-generated fixture record.
    with patch.object(writers,'now_iso',return_value=STAMP):
        writers.record_query_miss_if_empty(f.project,'context',f.query,{})
    backup(f.project,root/'initial.sqlite3')
    before=tables(root/'initial.sqlite3')
    originals={n:getattr(selection,n) for n in ('bind_validation_field_context','enrich_validation_field','accounting_validation_field')}
    original_use=writers.record_context_use;original_miss=writers.record_query_miss_if_empty
    original_terminal=handler.compact_context;original_usage=handler.record_query_usage
    original_perf=handler.append_performance_sample
    original_query_perf=handler.append_query_performance_sample
    original_save_usage=usage_writers.save_usage_sample
    original_save_task=usage_writers.save_task_trace

    def identity(project):
        actual={key:str(getattr(project,key)) for key in (
            "project_id","root","db_path","memory_home")}
        expected={key:str(getattr(f.project,key)) for key in actual}
        records.setdefault("writer_projects",[]).append(actual)
        assert actual==expected,"writer project identity mismatch"

    def save_usage(project,sample):
        identity(project)
        result=original_save_usage(project,sample)
        # The original updates timestamp/summary before writing and returns None.
        saved=deepcopy(sample)
        assert json.loads(usage_writers.usage_sample_path(project).read_text())==saved
        records.setdefault("saved_usage",[]).append(saved)
        return result

    def save_task(project,trace):
        identity(project)
        result=original_save_task(project,trace)
        saved=deepcopy(trace)
        assert json.loads(usage_writers.task_trace_path(project).read_text())==saved
        records.setdefault("saved_task",[]).append(saved)
        return result

    def mutate():
        if records['mutations']:raise AssertionError('mutation executed twice')
        path=f.project.root/'AccountDraftPanel.ts'
        path.write_bytes(path.read_bytes()+b'\n// independent late-source invalidation\n')
        records['mutations']+=1

    def bind(project,query,data,items,collection=None):
        records['ordinary_raw']=deepcopy(dict(data))
        result=originals['bind_validation_field_context'](project,query,data,items,collection)
        records['bind'].append(type(result).__qualname__)
        if not isinstance(result,selection.ValidationContext):
            raise AssertionError('case requires authentic pre-mutation private issuance')
        return result

    def enrich(data,*args,**kwargs):
        if stage=='before_enrich':mutate()
        result=originals['enrich_validation_field'](data,*args,**kwargs)
        records['enrich_private']=isinstance(result,selection.ValidationContext)
        return result

    def accounting(data):
        if stage=='before_accounting':mutate()
        result=originals['accounting_validation_field'](data)
        records['accounting_payload']=deepcopy(dict(result))
        return result

    def use(project,data):
        identity(project)
        backup(project,root/'pre-use.sqlite3')
        records['use'].append(deepcopy(dict(data)))
        return original_use(project,data)

    def miss(project,source,query,data):
        identity(project)
        records['miss'].append({'source':source,'query':query,'data':deepcopy(dict(data))})
        return original_miss(project,source,query,data)

    def terminal(data):
        if stage=='before_terminal_compact':
            assert len(records['use'])==len(records['miss'])==1
            mutate()
        from tools.agent_memory_runtime.context_compact import _compact_context
        ordinary_final=_compact_context(dict(data))
        result=original_terminal(data)
        assert result==ordinary_final, 'late invalidation must use exact ordinary final renderer'
        records['final_output']=deepcopy(result)
        return result

    def usage(project,command,query,data):
        identity(project)
        records['usage'].append(deepcopy(data))
        return original_usage(project,command,query,data)

    def performance(project,sample):
        identity(project)
        records['performance'].append(deepcopy(sample))
        return original_perf(project,sample)

    def query_performance(project,operation,started,data):
        identity(project)
        records.setdefault('performance_inputs',[]).append(deepcopy(data))
        return original_query_perf(project,operation,started,data)

    args=argparse.Namespace(project=str(f.project.root),memory_home=str(f.project.memory_home),
                            query=f.query,intent=None,compact=True,json=True)
    with patch.object(selection,'bind_validation_field_context',side_effect=bind), \
         patch.object(selection,'enrich_validation_field',side_effect=enrich), \
         patch.object(selection,'accounting_validation_field',side_effect=accounting), \
         patch.object(writers,'record_context_use',side_effect=use), \
         patch.object(writers,'record_query_miss_if_empty',side_effect=miss), \
         patch.object(writers,'now_iso',return_value=STAMP), \
         patch.object(handler,'compact_context',side_effect=terminal), \
         patch.object(handler,'record_query_usage',side_effect=usage), \
         patch.object(usage_writers,'save_usage_sample',side_effect=save_usage), \
         patch.object(usage_writers,'save_task_trace',side_effect=save_task), \
         patch.object(handler,'append_performance_sample',side_effect=performance), \
         patch.object(handler,'append_query_performance_sample',side_effect=query_performance), redirect_stdout(stdout):
        handler.context(args)
    backup(f.project,root/'after.sqlite3')
    after=tables(root/'after.sqlite3')
    assert records['mutations']==1 and len(records['bind'])==1
    assert len(records['use'])==len(records['miss'])==1
    assert records['miss'][0]['source']=='context' and records['miss'][0]['query']==f.query
    assert records['miss'][0]['data']==records['use'][0]
    actual=records['use'][0];ordinary=records['ordinary_raw']
    for name in ('semantic_facts','reflections','episodes'):
        assert actual.get(name,[])==ordinary.get(name,[])
    assert actual['wiki_matches'] and ordinary['wiki_matches']
    assert after['query_misses']==before['query_misses']
    expected=deepcopy(before)
    for name in ('semantic_facts','reflections','episodes'):
        ids=[r['id'] for r in actual.get(name,[])]
        for row in expected[name]:
            count=ids.count(row['id']) if row['project_id']==f.project.project_id else 0
            if count:row.update(use_count=(row['use_count'] or 0)+count,last_used_at=STAMP)
    assert expected==after, 'actual persistent effects not one exact use/miss pair'
    # Persistent-effects twin subtest deliberately duplicates a genuine memory
    # item in BOTH inputs. It does not forge/reissue a private context.
    left,right=deepcopy(ordinary),deepcopy(actual)
    available=next((name for name in ('episodes','semantic_facts','reflections') if left.get(name)),None)
    assert available is not None,'duplicate-ID fixture requires actual memory row'
    left[available].append(deepcopy(left[available][0]));right[available].append(deepcopy(right[available][0]))
    twin_results=[]
    for label,payload in [('ordinary',left),('adopted',right)]:
        dest=root/(label+'-twin.sqlite3');dest.write_bytes((root/'pre-use.sqlite3').read_bytes())
        twin=replace(f.project,db_path=dest)
        with patch.object(writers,'now_iso',return_value=STAMP):
            original_use(twin,payload);original_miss(twin,'context',f.query,payload)
        saved=root/(label+'-twin-after.sqlite3');backup(twin,saved)
        twin_results.append(tables(saved))
    assert twin_results[0]==twin_results[1], 'different duplicate-ID persistent effects'
    final=records['final_output']
    assert records['usage']==[final] and records['performance_inputs']==[final]
    assert len(records['saved_usage'])==len(records['saved_task'])==1
    assert json.loads(usage_writers.usage_sample_path(f.project).read_text())==records['saved_usage'][0]
    assert json.loads(usage_writers.task_trace_path(f.project).read_text())==records['saved_task'][0]
    assert json.loads(stdout.getvalue())==final
    assert json.loads((f.project.runtime_dir/'last_context.json').read_text())==redact_source_excerpt_bodies(final)
    perf=[json.loads(line) for line in (f.project.runtime_dir/'performance_samples.jsonl').read_text().splitlines()]
    assert len(records['performance'])==1 and perf[-1]==records['performance'][0]
    # Real final sidecar content and actual writer inputs are retained,
    # not normalized to the earlier adopted code view.
    records['sidecars']={p.name:p.read_text() for p in f.project.runtime_dir.iterdir() if p.is_file()}
    records['result']='PASS'
    return records


def run_case(stage,fresh_root):
    """Fresh output ownership precedes all setup/import/capability operations."""
    root=Path(fresh_root)
    if root.exists():raise ValueError('fresh case directory required')
    root.mkdir(parents=True)
    records={'stage':stage,'bind':[],'use':[],'miss':[],'usage':[],
             'performance':[],'mutations':0}
    stdout=io.StringIO()
    try:
        return _run_case(stage,root,records,stdout)
    except BaseException as error:
        records['result']='STOP'
        records['error']=type(error).__name__+': '+str(error)
        raise
    finally:
        (root/'stdout.txt').write_text(stdout.getvalue())
        (root/'RESULT.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':
    raise SystemExit('DRAFT: no execution authorized')
