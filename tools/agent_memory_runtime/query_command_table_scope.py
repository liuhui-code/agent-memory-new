# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Metadata-only candidate frames, not table authority or exhaustive retrieval."""
from pathlib import Path
from .storage import connect
from .query_output_loop_selection import valid_row
from .query_record_loop_selection import FIELDS

IDENTITY=(*FIELDS,'signature')
FILE_FIELDS=('id','project_id','file_path','language','source_digest','index_generation')


def same_fields(left,right,fields):
    return all(k in left and k in right and type(left[k])is type(right[k])and left[k]==right[k]for k in fields)


def symbol_alias(left,right):
    """Missing keys never assert identity; bool is not a record ID."""
    id_match=(type(left.get('id'))is int and left['id']>0 and
              type(right.get('id'))is int and left['id']==right['id'])
    key=left.get('symbol_key')
    key_match=isinstance(key,str)and bool(key)and isinstance(right.get('symbol_key'),str)and key==right['symbol_key']
    return id_match or key_match


def metadata_frames(project,pool):
    if type(pool)is not list or not pool or any(type(r)is not dict for r in pool):return None
    paths=set()
    for row in pool:
        name=row.get('file_path')
        if (row.get('kind')not in {'file','symbol'}or not isinstance(name,str)or not name
            or Path(name).is_absolute()or '..'in Path(name).parts):return None
        paths.add(name)
    with connect(project)as db:
        marks=','.join('?'for _ in paths);args=(project.project_id,*sorted(paths))
        # DB rows are equality/parent checks for original records, never recall.
        rows=[dict(r)for r in db.execute('SELECT * FROM code_symbols WHERE project_id=? AND file_path IN ('+marks+')',args)]
        files=[dict(r)for r in db.execute('SELECT * FROM code_files WHERE project_id=? AND file_path IN ('+marks+')',args)]
    symbols={};recalled_files={}
    for row in pool:
        if row['kind']=='file':
            matches=[r for r in files if r['id']==row.get('id')or r['file_path']==row['file_path']]
            if len(matches)!=1 or not same_fields(row,matches[0],FILE_FIELDS):return None
            recalled_files[row['file_path']]=matches[0]
        else:
            matches=[r for r in rows if symbol_alias(row,r)]
            if len(matches)!=1 or not same_fields(row,matches[0],IDENTITY):return None
            symbols[row['id']]=matches[0]
    groups={}
    for row in symbols.values():
        signature=row.get('signature');qualified=row.get('qualified_name')
        hinted=(isinstance(signature,str)and signature.startswith('callback'))or(isinstance(qualified,str)and '@'in qualified)
        if not hinted:continue
        parents=[r for r in rows if r['file_path']==row['file_path']and r['symbol']==row.get('owner_name')and r['symbol_type']in {'component','struct'}]
        if row.get('owner_kind')!='component'and not parents:continue
        if row.get('owner_kind')!='component'or len(parents)!=1:return None
        owner=parents[0];name=row.get('symbol');line=row.get('start_line')
        if (not valid_row(row,project)or not valid_row(owner,project)or row['symbol_type']not in {'function','method'}
            or owner['owner_kind']!='component'or owner.get('owner_name')not in ('',None)
            or owner['qualified_name']!=owner['symbol']or signature!='callback '+name+'@'+str(line)
            or qualified!=owner['symbol']+'.'+name+'@'+str(line)):return None
        groups.setdefault((row['file_path'],owner['id']),dict(owner=owner,callbacks={} ))['callbacks'][row['id']]=row
    frames=[]
    for (path,_),group in sorted(groups.items()):
        owner=group['owner'];callbacks=list(group['callbacks'].values());file=recalled_files.get(path)
        builds=[r for r in symbols.values()if r['file_path']==path and r.get('owner_name')==owner['symbol']and r.get('symbol')=='build']
        if file is None or len(builds)!=1:return None
        build=builds[0]
        if (not valid_row(build,project)or build['owner_kind']!='component'or build['qualified_name']!=owner['symbol']+'.build'
            or build['symbol_type']not in {'function','method'}or type(file['index_generation'])is not int):return None
        members=[owner,build,*callbacks]
        if len({r['id']for r in members})!=len(members)or len({r['symbol_key']for r in members})!=len(members):return None
        for row in members:
            if (row['source_digest']!=file['source_digest']or row['index_generation']!=file['index_generation']
                or not owner['start_line']<=row['start_line']<=row['end_line']<=owner['end_line']):return None
            aliases=[r for r in rows if symbol_alias(row,r)]
            if len(aliases)!=1 or not same_fields(aliases[0],row,IDENTITY):return None
        frames.append(dict(path=path,file=file,owner=owner,build=build,callbacks=callbacks,members=members))
    if not frames or len(frames)>12:return None
    return dict(frames=frames,pool_paths=tuple(sorted(paths)))
