import pathlib,json,sys,copy,hashlib,shutil
base=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(base.parent/'repo'))
from tools.agent_memory_runtime.storage import resolve_project
from tools.agent_memory_runtime.query_collect import collect_matches_with_audit
from tools.agent_memory_runtime.query_code_focus import focus_code_candidates,named_identity_candidates
from tools.agent_memory_runtime.query_code_selection import diverse_code_matches
from tools.agent_memory_runtime.query_language import positive_retrieval_query
home=base/'diagnostic-home';shutil.copytree(base/'seed',home)
p=resolve_project(str(base/'source'),str(home))
report={}
for name,q in json.load(open(base/'protocol.json'))['queries']:
 rows=collect_matches_with_audit(p,q).matches['wiki_matches']
 focused,active=focus_code_candidates(copy.deepcopy(rows),q)
 report[name]={'query':q,'positive':positive_retrieval_query(q),'rows':rows,'focused':focused,'activated':active}
(base/'diagnostic.json').write_text(json.dumps(report,indent=2))
for name,v in report.items():
 print(name,'named',[(x['file_path'],x.get('symbol')) for x in named_identity_candidates(v['rows'],v['query'])]); print('focused',[(x['file_path'],x.get('symbol'),x.get('match_reasons')) for x in v['focused']])
