"""Independent current candidate-log witnesses; never runtime causality authority."""
import json
import sqlite3
import re
import math
from .storage import connect
from .query_output_loop_selection import snapshot
from .query_ui_divider_wrapped_provenance import one, current, method, positive, path_ok


def projection(row, stored):
    for key, value in stored.items():
        actual = row.get(key)
        if key in ('call_path', 'call_path_locations'):
            value = json.loads(value)
        if type(actual) is not type(value) or actual != value:
            raise ValueError('candidate projection '+key)


def direct(db, project, row, witnesses):
    if not positive(row.get('id')): raise ValueError('direct identity')
    saved = one(db, 'code_log_statements', 'project_id=? AND id=?', (project.project_id,row['id']))
    projection(row,saved)
    source = current(db,project,saved,witnesses)
    if (not positive(saved['line']) or saved['line']>len(source.splitlines())
            or any(type(saved.get(k)) is not str or not saved[k] for k in
                   ('function','logger','level','message_template','raw_statement'))):
        raise ValueError('direct shape')
    return dict(row=saved)


def edge(db, project, caller, target, relation, target_type, index):
    result=one(db,'memory_edges',
        'project_id=? AND source_type=? AND source_id=? AND relation=? AND target_type=? AND target_id=? AND valid_to IS NULL',
        (project.project_id,'code_symbol',caller['id'],relation,target_type,target['id']))
    if (not positive(result['id']) or not result['valid_from']
            or result['source_revision']!=index['source_revision']
            or type(result.get('confidence')) not in (int,float)
            or not math.isfinite(result['confidence']) or not 0 <= result['confidence'] <= 1): raise ValueError('edge version')
    return result


def wrapped(db, project, row, index, witnesses):
    if not positive(row.get('id')):raise ValueError('effect id')
    saved=one(db,'code_log_effects','project_id=? AND id=?',(project.project_id,row['id']))
    projection(row,saved)
    depth=saved['wrapper_depth']; inferred=saved['evidence_class']=='inferred_wrapped'
    if (type(depth)is not int or depth not in (1,2) or saved['evidence_class'] not in ('static_wrapped','inferred_wrapped')
            or (inferred and depth!=1)
            or type(saved['truncated'])is not int or saved['truncated']!=0
            or not positive(saved['line']) or not positive(saved['sink_log_id'])):raise ValueError('unsupported effect')
    current(db,project,saved,witnesses)
    paths=json.loads(saved['call_path']);locations=json.loads(saved['call_path_locations'])
    if (type(paths)is not list or type(locations)is not list or len(paths)!=depth+2
            or len(locations)!=len(paths) or len(set(locations[:-1]))!=depth+1):raise ValueError('path shape')
    refs=[]
    for loc,name in zip(locations,paths):
        if type(loc)is not str or loc.count('#')!=1 or type(name)is not str or not name:raise ValueError('location')
        f,n=loc.split('#')
        if not path_ok(f) or n!=name:raise ValueError('location identity')
        refs.append((f,n))
    sink=one(db,'code_log_statements','project_id=? AND id=?',(project.project_id,saved['sink_log_id']))
    current(db,project,sink,witnesses)
    if (refs[0]!=(saved['file_path'],saved['function']) or paths[1]!=saved['wrapper_symbol']
            or refs[-2]!=(sink['file_path'],sink['function'])
            or refs[-1]!=(sink['file_path'],sink['logger']+'.'+sink['level'])
            or saved['logger']!=sink['logger'] or saved['level']!=sink['level']):raise ValueError('sink projection')
    methods=[]
    for i,(f,n)in enumerate(refs[:-1]):
        # Intermediate line is verified against the outgoing typed edge below.
        seed=one(db,'code_symbols','project_id=? AND file_path=? AND symbol=? AND symbol_type=?',(project.project_id,f,n,'function'))
        line=saved['line']if i==0 else sink['line']if i==depth else seed['start_line']
        methods.append(method(db,project,f,n,line,witnesses))
    if len({s['id']for s in methods})!=len(methods):raise ValueError('cycle')
    calls=[]
    for i,(a,b)in enumerate(zip(methods,methods[1:])):
        call=edge(db,project,a,b,'calls','code_symbol',index);proof=json.loads(call['evidence'])
        if (type(proof)is not dict or proof.get('schema_version')!='semantic-evidence/v1'
                or proof.get('evidence_class')!=('inferred' if inferred else 'static')
                or (inferred and not 0 < call['confidence'] <= 0.55) or not positive(proof.get('line'))
                or not a['start_line']<=proof['line']<=a['end_line']
                or (i==0 and proof['line']!=saved['line'])
                or proof.get('source_digest')!=a['source_digest']
                or proof.get('adapter')!=a['semantic_adapter']
                or call['evidence_kind']!=('inferred_semantic_calls' if inferred else 'static_semantic_calls')
                or call['extractor_version']!='semantic-index:v1/'+a['semantic_adapter']):raise ValueError('typed call evidence')
        source=current(db,project,a,witnesses)
        call_line=source.splitlines()[proof['line']-1]
        if not re.search(r'\.\s*'+re.escape(b['symbol'])+r'\s*\(',call_line):
            raise ValueError('call line does not contain target invocation')
        calls.append(call)
    emits=edge(db,project,methods[-1],sink,'emits_log','code_log_statement',index)
    if (emits['extractor_version']!='code-wiki:v4' or emits['evidence_kind']!='code_observability'
            or emits['evidence']!=sink['file_path']+':'+str(sink['line'])):raise ValueError('emits evidence')
    return dict(row=saved,sink=sink,methods=methods,calls=calls,emits=emits)


def visible(log, item, is_effect):
    row=item['row']
    for key in ('file_path','function','line','logger','message_template'):
        if type(log.get(key))is not type(row[key])or log[key]!=row[key]:raise ValueError('visible projection')
    if 'level'in log and log['level']!=row['level']:raise ValueError('visible level')
    if log.get('truncated')is not False:raise ValueError('truncated projection')
    if is_effect:
        for key in ('wrapper_symbol','wrapper_depth','evidence_class'):
            if type(log.get(key))is not type(row[key])or log[key]!=row[key]:raise ValueError('effect projection')
        for key in ('call_path','call_path_locations'):
            if log.get(key)!=json.loads(row[key]):raise ValueError('effect path projection')
        if not positive(log.get('log_id')) or log['log_id']!=row['sink_log_id']:raise ValueError('visible sink')
    elif (log.get('evidence_class')!='direct' or log.get('effect_id')is not None
          or log.get('wrapper_symbol')is not None or log.get('wrapper_depth')is not None
          or log.get('call_path')!=[] or log.get('call_path_locations')!=[]):raise ValueError('direct projection')


def touch_log_provenance(project, inventory, logs):
    """Bind all supplied collection rows plus visible logs; issuer proves coverage."""
    try:
        if (type(inventory)is not dict or set(inventory)!={'direct','effects'} or type(logs)is not list
                or any(type(inventory[k])is not list for k in inventory)):return None
        witnesses=[];items={}
        with connect(project)as db:
            db.execute('BEGIN')
            index=one(db,'code_index_state','project_id=?',(project.project_id,))
            graph=one(db,'graph_runtime_state','project_id=?',(project.project_id,))
            if (index['status']!='active' or not positive(index['generation']) or not positive(graph['graph_revision'])
                    or type(index['source_revision'])is not str or not index['source_revision']
                    or index['extractor_version']!='code-derived:v1'):return None
            for kind in ('direct','effects'):
                for row in inventory[kind]:
                    if type(row)is not dict or not positive(row.get('id'))or(kind,row['id'])in items:return None
                    items[kind,row['id']]=direct(db,project,row,witnesses)if kind=='direct'else wrapped(db,project,row,index,witnesses)
            seen=set()
            for log in logs:
                if type(log)is not dict:return None
                is_effect=log.get('effect_id')is not None
                ident=log.get('effect_id')if is_effect else log.get('log_id');key=('effects'if is_effect else'direct',ident)
                if not positive(ident)or key not in items or key in seen:return None
                seen.add(key);visible(log,items[key],is_effect)
            if any(w['file']['index_generation']>index['generation']for w in witnesses):return None
        return snapshot(dict(contract='touch-candidate-log-provenance/v1',inventory=inventory,logs=logs,
            items=[dict(kind=k[0],id=k[1],witness=v)for k,v in items.items()],files=witnesses,index=index,graph=graph))
    except(AttributeError,KeyError,TypeError,ValueError,OSError,UnicodeError,sqlite3.Error,OverflowError):return None
