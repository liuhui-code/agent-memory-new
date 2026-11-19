"""Command-local empty-context addition and one final accounting commit.

No global index marker, common ranking, or direct limited_context behavior changes.
"""
from contextvars import ContextVar
from copy import deepcopy
from pathlib import Path
import hashlib
import re
import sqlite3
import time
from .storage import connect
from .receiver_iteration_hint import receiver_iteration_terms, receiver_iteration_update
from .query_output_loop_selection import valid_row

_active = ContextVar('receiver_empty_command', default=None)


def inventory(project):
    start = time.monotonic()
    try:
        with connect(project) as conn:
            conn.set_progress_handler(lambda: int(time.monotonic()-start > .2), 1000)
            conn.execute('BEGIN')
            state = conn.execute('SELECT * FROM code_index_state WHERE project_id=?', (project.project_id,)).fetchone()
            files = [dict(r) for r in conn.execute('SELECT * FROM code_files WHERE project_id=? ORDER BY id LIMIT 13', (project.project_id,))]
            symbols = [dict(r) for r in conn.execute('SELECT * FROM code_symbols WHERE project_id=? ORDER BY id LIMIT 257', (project.project_id,))]
            if state is None or state['status'] != 'active': return None
            state = dict(state)
        rows = [r for r in symbols if r['symbol_type'] in {'function','method'}]
        if not 0 < len(files) <= 12 or len(symbols) > 256 or len(rows) > 128: return None
        keys = [r.get('symbol_key') for r in symbols]
        if len(set(keys)) != len(keys): return None
        return files, rows, symbols, state
    except sqlite3.Error:
        return None


def empty_eligible(data):
    h = data.get('query_handoff', {})
    c=h.get('callable_evidence') if type(h) is dict else None
    return (type(h) is dict and h.get('code_anchors') == []
            and type(c) is dict and c.get('primary') is None and c.get('alternatives') == []
            and data.get('source_freshness', {}).get('status') in {'current','empty'}
            and receiver_iteration_terms(data.get('query')))


def authenticate(project, data, state, deadline=None):
    if not empty_eligible(data) or state is None: return None
    deadline = time.monotonic()+.5 if deadline is None else deadline
    files, rows, symbols, index = state
    root = Path(project.root).resolve()
    generation = data['source_freshness'].get('generation')
    if index['generation'] != generation: return None
    anchors, members = [], []
    total_bytes = 0
    for f in files:
        if time.monotonic()>deadline: return None
        name = f['file_path']; path = (root/name).resolve()
        if not path.is_relative_to(root) or f.get('index_generation') != generation: return None
        try:
            with path.open('rb') as stream: raw = stream.read(256*1024+1)
            total_bytes += len(raw)
            if len(raw)>256*1024 or total_bytes>1024*1024 or hashlib.sha256(raw).hexdigest()!=f.get('source_digest'): return None
            source = raw.decode('utf-8')
        except (OSError,UnicodeError): return None
        if path.suffix not in {'.ets','.ts'}: continue
        lines=source.split('\n')
        for row in [r for r in rows if r['file_path']==name]:
            if (not valid_row(row,project) or row.get('source_digest')!=f['source_digest']
                    or row.get('index_generation')!=generation or row['end_line']>len(lines)): return None
            lo,hi=row['start_line'],row['end_line']; text='\n'.join(lines[lo-1:hi])
            if not receiver_iteration_update(text,row['symbol']): continue
            owners=[o for o in symbols if o['file_path']==name and o['symbol']==row.get('owner_name')
                    and o['symbol_type'] in {'class','struct','component'}]
            if len(owners)!=1: return None
            owner=owners[0]
            if (not valid_row(owner,project) or owner['source_digest']!=f['source_digest']
                    or owner['index_generation']!=generation or owner['end_line']>len(lines)
                    or owner.get('owner_name') not in ('',None) or owner['qualified_name']!=owner['symbol']
                    or row.get('owner_kind')!=owner.get('owner_kind')
                    or not owner['start_line']<=lo<=hi<=owner['end_line']
                    or row['qualified_name']!=owner['symbol']+'.'+row['symbol']
                    or not re.search(r'\b(?:class|struct)\s+'+re.escape(owner['symbol'])+r'\b',lines[owner['start_line']-1])): return None
            span=dict(symbol=row['symbol'],start_line=lo,end_line=hi)
            anchors.append(dict(file_path=name,symbol=row['symbol'],symbol_type=row['symbol_type'],
                record_ids=[row['id']],record_type='code_symbol',source_ranges=[span],
                read_window=dict(start_line=lo,end_line=hi),role='supporting',
                source_snapshot=dict(index_generation=generation,source_digest=f['source_digest']),
                source_excerpts=[dict(span,content=text,source='validated_request_snapshot',
                    selection_reason='complete_direct_receiver_callback_syntax',focus_line=None,truncated=False)]))
            members.append(dict(row,kind='symbol'))
    return (anchors,members) if 0<len(anchors)<=2 else None


def defer_accounting(project,query,data):
    session=_active.get()
    if (session is None or session.project!=project or session.query!=query
            or session.baseline is not None or type(data) is not dict or not empty_eligible(data)):
        return False
    session.baseline=deepcopy(data)
    return True


class EmptyReceiverSession:
    def __init__(self,project,query):
        self.project=project; self.query=query; self.baseline=None; self.done=False
    def __enter__(self):
        self.token=_active.set(self); return self
    def __exit__(self,kind,value,trace):
        try:
            if self.baseline is not None and not self.done: self.commit(self.baseline)
        finally: _active.reset(self.token)
    def commit(self,adopted):
        from .query_results import record_context_use,record_query_miss_if_empty
        if self.done: raise RuntimeError('empty receiver accounting already committed')
        # Once-attempt: failure propagates, never repeat a possibly committed write.
        self.done=True
        record_context_use(self.project,adopted)
        record_query_miss_if_empty(self.project,'context',self.query,adopted)
    def finalize(self,output):
        if self.baseline is None: return output
        from .context_record_loop_transaction import apply_record_loop_transaction
        from .context_compact import compact_context
        deadline=time.monotonic()+.5
        state=inventory(self.project)
        qualified=authenticate(self.project,self.baseline,state,deadline)
        adopted=self.baseline
        result=output
        if (qualified is not None and output.get('query_handoff',{}).get('code_anchors')==[]
                and inventory(self.project)==state
                and authenticate(self.project,self.baseline,state,deadline)==qualified
                and time.monotonic()<=deadline):
            anchors,members=qualified
            compact=output if 'output_budget' in output else compact_context(output)
            candidate=apply_record_loop_transaction(compact,anchors)
            if candidate is not compact:
                adopted=deepcopy(self.baseline)
                adopted['wiki_matches']=[*adopted.get('wiki_matches',[]),*members]
                adopted['query_handoff']['code_anchors']=deepcopy(anchors)
                if 'output_budget' in output: result=candidate
                else:
                    result=deepcopy(output)
                    result['wiki_matches']=[*result.get('wiki_matches',[]),*members]
                    for key in ('code_anchors','callable_evidence','source_excerpt_policy'):
                        result['query_handoff'][key]=deepcopy(candidate['query_handoff'][key])
                    from .context_compact import evidence_gaps
                    from .context_sufficiency import diagnosis_sufficiency
                    result['evidence_gaps']=evidence_gaps(result['query_handoff'])
                    result['sufficiency']=diagnosis_sufficiency(result['query_handoff'],result['evidence_gaps'],result.get('source_freshness'))
        self.commit(adopted)
        return result
