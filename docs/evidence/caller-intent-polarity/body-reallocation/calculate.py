import sys,json,pathlib,copy,itertools
B=pathlib.Path(__file__).resolve().parent.parent;sys.path.insert(0,str(B/'repo/tools'))
from agent_memory_runtime.context_budget import synchronize_estimate
from agent_memory_runtime.performance_scoring import estimate_payload_tokens
S=B/'original13/source'; O=pathlib.Path(__file__).parent
p32=json.load(open(B/'current32-after-body/output.json'));p13=json.load(open(B/'recall-audit13/clean-default.json'))
def finish(d):
 h=d['query_handoff'];ex=[e for a in h['code_anchors'] for e in a.get('source_excerpts',[])];h['source_excerpt_policy'].update(excerpt_count=len(ex),excerpt_chars=sum(len(e['content'])for e in ex));synchronize_estimate(d);return estimate_payload_tokens(d)
def body(path,lo,hi,old):
 e=copy.deepcopy(old);e.update(start_line=lo,end_line=hi,content='\n'.join((S/path).read_text().splitlines()[lo-1:hi]),truncated=True);return e
def narrow(d,idx,span):
 a=d['query_handoff']['code_anchors'][idx];old=a['source_excerpts'][0]
 if span is None:
  a.pop('source_excerpts');a['read_window']=dict(start_line=old['start_line'],end_line=old['end_line'])
 else:a['source_excerpts']=[body(a['file_path'],*span,old)]
 # Preserve the full original displayed interval as a follow-up range; otherwise binding outside method may become undiscoverable from metadata alone.
 prior=a.get('read_window',{});a['read_window']=dict(start_line=min(prior.get('start_line',old['start_line']),old['start_line']),end_line=max(prior.get('end_line',old['end_line']),old['end_line']))
res=[]
for target in [(9,17),(8,18)]:
 for toolbar in ['keep',(3,8),None]:
  for log in ['keep',(10,12),None]:
   d=copy.deepcopy(p32);a=d['query_handoff']['code_anchors'][0];a['source_excerpts']=[body(a['file_path'],*target,a['source_excerpts'][0])];a['source_excerpts'][0]['truncated']=False
   for i,v in [(1,toolbar),(2,log)]:
    if v!='keep':narrow(d,i,v)
   n=finish(d);name=f'32-{target}-{toolbar}-{log}';res.append(dict(name=name,tokens=n,within=n<=1500));(O/(str(len(res))+'.json')).write_text(json.dumps(d,ensure_ascii=False,indent=2))
nav=next(a for a in json.load(open(B/'original13/preserve2000.json'))['query_handoff']['code_anchors']if a['file_path']=='src/pages/AccountSettingsPage.ets');e=dict(symbol='saveAccount',start_line=9,end_line=15,content='\n'.join((S/nav['file_path']).read_text().splitlines()[8:15]),source='current_worktree',selection_reason='authenticated_graph_field_body',focus_line=None,truncated=False)
for order in ['keep',(9,12),None]:
 for job in ['keep',(7,14),None]:
  for wrapped in ['keep',(6,8),None]:
   d=copy.deepcopy(p13)
   for i,v in enumerate([order,job,wrapped]):
    if v!='keep':narrow(d,i,v)
   add=copy.deepcopy(nav);add['source_excerpts']=[e];d['query_handoff']['code_anchors'].append(add);n=finish(d);name=f'13-{order}-{job}-{wrapped}';res.append(dict(name=name,tokens=n,within=n<=1500));(O/(str(len(res))+'.json')).write_text(json.dumps(d,ensure_ascii=False,indent=2))
(O/'calculations.json').write_text(json.dumps(res,indent=2));print(json.dumps(res,indent=2))
