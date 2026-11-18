from pathlib import Path
import json,subprocess,copy
p=Path('../default-envelope-fixture').resolve();spec=json.loads((p/'protocol.json').read_text());results={}
for n,q in spec['queries'].items():
 r=subprocess.run(['python3','-B','tools/agent_memory.py','context','--project',str(p/'source'),'--memory-home',str(p/'seed'),'--query',q,'--compact','--json'],capture_output=True,text=True);(p/'after'/(n+'.json')).write_text(r.stdout);(p/'after'/(n+'.stderr')).write_text(r.stderr);assert r.returncode==0
 a=json.loads((p/(n+'-compact.json')).read_text());b=json.loads(r.stdout);result={'before':a['output_budget'],'after':b['output_budget'],'exact_noop':a==b}
 if n=='binding':
  z=copy.deepcopy(b);e=z['query_handoff']['code_anchors'][0]['source_excerpts'][0];old=e['expanded_from'];old['content']='\n'.join(e['content'].splitlines()[old['start_line']-e['start_line']:old['end_line']-e['start_line']+1]);z['query_handoff']['code_anchors'][0]['source_excerpts'][0]=old;z['query_handoff']['source_excerpt_policy']=a['query_handoff']['source_excerpt_policy'];z['output_budget']=a['output_budget'];result['exact_restoration']=z==a;result['new_ranges']=[(e['start_line'],e['end_line'])for e in b['query_handoff']['code_anchors'][0]['source_excerpts']]
 results[n]=result
(p/'after/verification.json').write_text(json.dumps(results,indent=2));print(results)
