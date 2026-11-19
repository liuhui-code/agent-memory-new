from pathlib import Path
import json,copy,hashlib
O=Path(__file__).resolve().parent

def reverse(new,old):
 r=copy.deepcopy(new)
 r['project_id']=old['project_id']
 for a in r['query_handoff']['code_anchors']:
  for i,e in enumerate(a.get('source_excerpts',[])):
   if 'expanded_from' in e:
    prior=dict(e['expanded_from']);prior['content']='\n'.join(e['content'].split('\n')[prior['start_line']-e['start_line']:prior['end_line']-e['start_line']+1]);a['source_excerpts'][i]=prior
 r['query_handoff']['source_excerpt_policy']=old['query_handoff']['source_excerpt_policy'];r['output_budget']=old['output_budget'];return r==old
out=[]
for b,a in zip(json.loads((O/'baseline.json').read_text()),json.loads((O/'candidate.json').read_text())):
 old=b['outputs']['compact'];new=a['outputs']['compact'];ok=reverse(new,old);assert ok
 out.append(dict(fixture=b['fixture'],query=b['query']['id'],unchanged=old==new,all_old_data_recoverable=ok,before=old['output_budget'],after=new['output_budget']))
for n in [1,3,5]:
 old=json.loads((O.parent/'historical14-current'/f'captured-{n}.json').read_text())['payload'];new=json.loads((O/'original-after'/f'captured-{n}.json').read_text())['payload'];ok=reverse(new,old);assert ok
 out.append(dict(original14_capture=n,unchanged=old==new,all_old_data_recoverable=ok,before=old['output_budget'],after=new['output_budget']))
assert json.loads((O.parent/'historical14-current/materialized-files.json').read_text())==json.loads((O/'original-after/materialized-files.json').read_text())
(O/'comparison.json').write_text(json.dumps(out,indent=2))
print('Independent6 + original3 old evidence reversible; source manifest identical157')
