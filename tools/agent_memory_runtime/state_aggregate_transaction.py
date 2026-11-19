"""Optional2000 source supplements, not unique reactive ownership or causality."""
import re,time,sqlite3
from .receiver_iteration_hint import IDENT,receiver_iteration_update

def request(query):
 if not isinstance(query,str)or len(query)>300:return False
 # Full observation grammar, not arbitrary preface minus forbidden words.
 # Labels are symptom subjects only; they grant no source/owner exclusion.
 english=re.fullmatch(
  r'(?:(?:Changing|Switching) the selected [a-z]{1,24} (?:leaves|keeps) '
  r'[a-z]{1,24}(?: and [a-z]{1,24})? totals (?:unchanged|stale)\. )?'
  r'(?:[Ff]ind|[Ll]ocate|[Rr]eturn) (?:the )?reactive aggregation (?:owner|source)\.?',query.strip(),re.ASCII)
 chinese=re.fullmatch(
  r'(?:(?:切换[\u4e00-\u9fff]{1,8}后[\u4e00-\u9fff]{1,12}汇总不刷新|当前汇总值未变化)，)?'
  r'(?:请)?(?:定位|查找|返回)状态聚合源码(?:，不要返回数据实体)?[。.]?',query.strip())
 if chinese:
  prefix=query.split('，',1)[0] if '，'in query else ''
  if any(t in prefix for t in ('只','仅','不要','排除','除外','不是','而是','比较','对比','限定')):return False
 return bool(english or chinese)


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
 if any(m.get('owner_name')==owner['symbol'] and m.get('symbol')in fields for m in methods):return False
 updates=set(re.findall(r'this\.('+IDENT+r')\s*\+=',body))
 return bool(updates)and all(fields.get(n)is True for n in updates)


def eligible(data):
 return (type(data)is dict and request(data.get('query'))
         and data.get('source_freshness',{}).get('status')in {'current','empty'})


def allowed_candidates(data):
 h=data.get('query_handoff',{});ev=h.get('callable_evidence',{})
 if h.get('code_anchors')==[] and ev.get('primary')is None and ev.get('alternatives')==[]:return None
 candidates=[c for c in [ev.get('primary'),*ev.get('alternatives',[])]if isinstance(c,dict)]
 allowed=set()
 for c in candidates:
  b=c.get('source_range',{});lo,hi=b.get('start_line'),b.get('end_line')
  if (all(isinstance(c.get(k),str)and c[k] for k in ['file_path','symbol','owner_name'])
      and c.get('owner_kind')=='component' and b.get('selection_reason')=='callable_symbol_range'
      and type(lo)is int and type(hi)is int and 0<lo<=hi):
   allowed.add((c['file_path'],c['owner_name'],c['symbol'],lo,hi))
 return allowed


def finalize(project,baseline,output):
 try:return _finalize(project,baseline,output)
 except(KeyError,TypeError,ValueError,AttributeError,OSError,UnicodeError,sqlite3.Error):return output,[]


def _finalize(project,baseline,output):
 from .receiver_empty_transaction import inventory,authenticate
 from .context_record_loop_transaction import apply_record_loop_transaction
 from .render_additive_transaction import append_passages
 if not eligible(baseline)or output.get('output_budget',{}).get('target_tokens')!=2000:return output,[]
 allowed=allowed_candidates(baseline)
 if allowed==set():return output,[]
 paths=None if allowed is None else sorted({a[0]for a in allowed})
 deadline=time.monotonic()+.5;state=inventory(project,paths=paths)
 qualified=authenticate(project,baseline,state,deadline,state_bound=True,allowed=allowed)
 if qualified is None:return output,[]
 anchors,members,receipts=qualified
 h=output.get('query_handoff',{});ev=h.get('callable_evidence',{})
 if (allowed is None and h.get('code_anchors')==[] and type(ev)is dict
     and ev.get('primary')is None and ev.get('alternatives')==[]):
  candidate=apply_record_loop_transaction(output,anchors);added=members if candidate is not output else []
 else:
  candidate,added=append_passages(output,receipts,selection_reason='static_state_receiver_update',anchor_role='supporting')
 if candidate is output:return output,[]
 if (inventory(project,paths=paths)!=state or authenticate(project,baseline,state,deadline,state_bound=True,allowed=allowed)!=qualified
     or time.monotonic()>deadline):return output,[]
 return candidate,added
