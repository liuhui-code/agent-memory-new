"""Read-only qualification experiment. Does not modify public serving output."""
from pathlib import Path
import sys,json,re
O=Path(__file__).resolve().parent;R=O.parent/'repo';sys.path.insert(0,str(R/'tools'))
from agent_memory_runtime.receiver_iteration_hint import receiver_iteration_update,IDENT
from agent_memory_runtime.storage import resolve_project,connect


def state_binding(source,row,owner,methods):
 if owner.get('symbol_type')not in {'struct','component'}or owner.get('owner_kind')!='component':return False
 lines=source.split('\n');body='\n'.join(lines[row['start_line']-1:row['end_line']])
 if not receiver_iteration_update(body,row['symbol']):return False
 first=min(m['start_line']for m in methods if m.get('owner_name')==owner['symbol'])
 fields={}
 for line in lines[owner['start_line']:first-1]:
  if not line.strip():continue
  state=re.fullmatch(r'\s*@State\s+('+IDENT+r')\s*:\s*number\s*=\s*0\s*;?\s*',line)
  # Other numeric initializers are allowed for non-updated context state.
  other=re.fullmatch(r'\s*@State\s+('+IDENT+r')\s*:\s*number\s*=\s*[0-9]+\s*;?\s*',line)
  array=re.fullmatch(r'\s*(?:private\s+)?('+IDENT+r')\s*:\s*'+IDENT+r'\[\]\s*=\s*\[\]\s*;?\s*',line)
  m=state or other or array
  if m is None or m[1]in fields:return False
  fields[m[1]]=bool(state or other)
 updates=set(re.findall(r'this\.('+IDENT+r')\s*\+=',body))
 return bool(updates)and all(fields.get(n)is True for n in updates)


def inspect(root,home):
 p=resolve_project(str(root),str(home));result=[]
 with connect(p)as c:rows=[dict(r)for r in c.execute('SELECT * FROM code_symbols WHERE project_id=?',(p.project_id,))]
 for row in rows:
  if row.get('symbol_type')not in {'method','function'}:continue
  owners=[o for o in rows if o.get('symbol')==row.get('owner_name')and o['file_path']==row['file_path']and o.get('symbol_type')in {'struct','component'}]
  if len(owners)!=1:continue
  source=(root/row['file_path']).read_text();methods=[m for m in rows if m['file_path']==row['file_path']and m.get('symbol_type')in {'method','function'}]
  if state_binding(source,row,owners[0],methods):result.append(dict(path=row['file_path'],symbol=row['symbol'],span=[row['start_line'],row['end_line']]))
 return result
if __name__=='__main__':
 out={d:inspect(O/d,O/(d+'-memory'))for d in ['Warehouse','Energy']}
 out['standard157']=inspect(O.parent/'render05-current-contract/source',O.parent/'render05-current-contract/memory')
 (O/'source-proof.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
