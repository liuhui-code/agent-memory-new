# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Request-bound non-erasure of two already admitted UI declarations."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from .storage import connect
from .text import identifier_parts

WORD = r'[a-z]+(?:[ -][a-z]+){0,2}'
FORMS = [rf'Return both UI source contexts for (?P<a>{WORD}) and (?P<b>{WORD})\.?',
         rf'Locate the typography code for (?P<a>{WORD}) and (?P<b>{WORD})\.?',
         rf'(?P<a>{WORD}) and (?P<b>{WORD}) render inconsistent text sizes\. Return both UI source contexts\.?']
RESERVED = set('and or not only both except exclude instead without return find locate source code context generate instruction call caller wrapper'.split())
ID_FIELDS = ('id','project_id','symbol_key','file_path','symbol','qualified_name',
             'start_line','end_line','source_digest','index_generation')


def pair_request(query):
    if not isinstance(query,str) or len(query)>400:
        return None
    for form in FORMS:
        match=re.fullmatch(form,query,re.I)
        if match:
            pair=tuple(tuple(re.split('[ -]',match[k].casefold()))for k in ('a','b'))
            if pair[0]!=pair[1] and not any(w in RESERVED for words in pair for w in words):
                return pair
    return None


def spelling_matches(words,name):
    if not isinstance(name,str) or re.fullmatch('[A-Za-z]+',name) is None:
        return False
    parts=identifier_parts(name) or [name.casefold()]
    if len(words)!=len(parts):
        return False
    for word,part in zip(words,parts):
        variants={word}
        if len(word)>4 and word.endswith('ies'):
            variants.add(word[:-3]+'y')
        elif len(word)>=4 and word.endswith('s') and not word.endswith(('ss','us','is')):
            variants.add(word[:-1])
        if part not in variants:
            return False
    return True


def snapshot(anchors):
    return json.dumps(anchors,sort_keys=True,ensure_ascii=False)


class PairHandoff(dict):
    def __copy__(self):
        return dict(self)
    def __deepcopy__(self,memo):
        return deepcopy(dict(self),memo)


def valid_row(row,project):
    return (type(row.get('id'))is int and row['id']>0
            and row.get('project_id')==project.project_id
            and type(row.get('index_generation'))is int and row['index_generation']>0
            and all(isinstance(row.get(k),str)and row[k] for k in ('symbol_key','file_path','symbol','qualified_name'))
            and type(row.get('start_line'))is int and type(row.get('end_line'))is int
            and 0<row['start_line']<=row['end_line']
            and re.fullmatch('[0-9a-f]{64}',str(row.get('source_digest')or''))is not None
            and row.get('evidence_class') in {'static','exact'}
            and str(row.get('semantic_adapter')or'').partition('@')[0]=='arkts-static')


def bind_from_rows(project,query,handoff,rows,files):
    pair=pair_request(query);anchors=handoff.get('code_anchors')or[]
    if pair is None or not anchors or len(anchors)>12:
        return handoff
    declarations=[r for r in rows if r.get('symbol_type') in {'component','struct'} and r.get('owner_kind')=='component']
    chosen=[]
    for words in pair:
        matching=[r for r in declarations if spelling_matches(words,r.get('symbol'))]
        if len(matching)!=1 or not valid_row(matching[0],project):
            return handoff
        chosen.append(matching[0])
    if chosen[0]['id']==chosen[1]['id']:
        return handoff
    proof=[];reads={};root=Path(project.root).resolve()
    for owner in chosen:
        path=owner['file_path'];file_rows=[f for f in files if f.get('file_path')==path]
        if len(file_rows)!=1 or any(file_rows[0].get(k)!=owner[k]for k in ('source_digest','index_generation')):
            return handoff
        try:
            file=(root/path).resolve()
            if not file.is_relative_to(root) or file.suffix!='.ets' or file.stat().st_size>2*1024*1024:
                return handoff
            if path not in reads:
                raw=file.read_bytes()
                if len(raw)>2*1024*1024:
                    return handoff
                reads[path]=(hashlib.sha256(raw).hexdigest(),len(raw.decode('utf-8').splitlines()))
        except (OSError,UnicodeError):
            return handoff
        digest,lines=reads[path]
        if digest!=owner['source_digest'] or owner['end_line']>lines:
            return handoff
        represented=[]
        for anchor in anchors:
            if anchor.get('file_path')!=path:
                continue
            candidates=[r for r in rows if r.get('file_path')==path and r.get('symbol')==anchor.get('symbol')
                        and r.get('start_line')==anchor.get('start_line') and r.get('end_line')==anchor.get('end_line')]
            if len(candidates)!=1:
                continue
            row=candidates[0]
            if not valid_row(row,project) or any(row[k]!=owner[k]for k in ('source_digest','index_generation')):
                continue
            direct=row['id']==owner['id'] and row.get('symbol_type') in {'component','struct'}
            method=(row.get('symbol_type') in {'method','function'} and row.get('owner_kind')=='component'
                    and row.get('owner_name')==owner['symbol'] and row.get('qualified_name')==owner['symbol']+'.'+row['symbol'])
            if (direct or method) and owner['start_line']<=row['start_line']<=row['end_line']<=owner['end_line']:
                represented.append(tuple(row.get(k)for k in ID_FIELDS))
        if not represented:
            return handoff
        proof.append((tuple(owner.get(k)for k in ID_FIELDS),tuple(represented)))
    result=PairHandoff(handoff);result._query=query;result._anchors=snapshot(anchors);result._proof=tuple(proof)
    result._binding=(query,result._anchors,result._proof)
    return result


def bind_ui_pair(project,query,handoff):
    if pair_request(query)is None:
        return handoff
    paths=sorted({a.get('file_path')for a in handoff.get('code_anchors')or[] if isinstance(a.get('file_path'),str)and a['file_path']})
    if not paths or len(paths)>12:
        return handoff
    marks=','.join('?'for _ in paths)
    with connect(project)as conn:
        rows=[dict(r)for r in conn.execute(f'SELECT * FROM code_symbols WHERE project_id=? AND file_path IN ({marks})',(project.project_id,*paths))]
        files=[dict(r)for r in conn.execute(f'SELECT file_path,source_digest,index_generation FROM code_files WHERE project_id=? AND file_path IN ({marks})',(project.project_id,*paths))]
    return bind_from_rows(project,query,handoff,rows,files)


def retains_ui_pair(handoff,anchors,query,path):
    if (not isinstance(handoff,PairHandoff) or pair_request(query)is None
            or path.get('activated') or path.get('wrapped_log_evidence')
            or any(a.get('log_identity_match')for a in anchors)):
        return False
    current=(query,snapshot(anchors),getattr(handoff,'_proof',None))
    return (current==getattr(handoff,'_binding',None)
            and getattr(handoff,'_query',None)==query
            and getattr(handoff,'_anchors',None)==current[1])


def preserve_ui_pair(handoff,anchors,focused,query,path):
    if not retains_ui_pair(handoff,anchors,query,path):
        return focused
    for owner,represented in handoff._proof:
        complete=False
        for row in represented:
            file_path,start,end=row[3],row[6],row[7]
            complete=complete or any(
                a.get('file_path')==file_path
                and type(a.get('start_line'))is int and type(a.get('end_line'))is int
                and a['start_line']<=start<=end<=a['end_line']
                for a in focused)
        if not complete:
            return anchors
    return focused
