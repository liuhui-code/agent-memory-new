# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
# Internal diagnosis only: same saved SQLite rows/source; no CLI/query rerun.
import json,sys
from pathlib import Path
D=Path(__file__).resolve().parent
work=Path(json.loads((D/'capacity-run.txt').read_text())['workspace']);sys.path.insert(0,str(work/'runtime'))
from tools.agent_memory_runtime.listener_display import diagnose
results=json.loads((D/'capacity-results.json').read_text());out=[]
for c in results:
    states=[diagnose(r,work/c['id'])for r in sorted(c['rows'],key=lambda r:r['id'])[:64]]
    count=sum(len(d['facts'])for d in states if d['status']=='current-source-slices-checked')
    out.append({'id':c['id'],'actual_context_unknown_cap':c['checks']['unknown_cap'],'source_check_count_same_saved_rows':count,'intended_fact_branch_confirmed':count>64 if c['id']=='fact-cap' else count<=64,'interpretation':'initial attribution reused list diagnostic (DESC first64), unlike context ASC first64; actual CLI results unchanged'})
(D/'capacity-attribution.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
