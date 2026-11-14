# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json
from pathlib import Path
D=Path(__file__).resolve().parent
traces=[json.loads(x)for x in (D/'consumer-trace.jsonl').read_text().splitlines()]
protocol=json.loads((D/'consumer-protocol.json').read_text());summary=json.loads((D/'consumer-summary.json').read_text());out=[]
for case in protocol['controls']:
    rows=[t for t in traces if Path(t['project']).name==case['id']]
    checks={'trace_present':bool(rows),'same_selected_set':all(sorted(map(str,t['before']))==sorted(map(str,t['after']))for t in rows)}
    if case['safety_oracle'].get('no_new_weak'):checks['no_new_weak']=all(not t['weak']for t in rows)
    if case['safety_oracle'].get('selected_order_unchanged'):checks['selected_order_unchanged']=all(t['before']==t['after']for t in rows)
    if case['safety_oracle'].get('two_forwarders_retained'):checks['two_forwarders_retained']=all(len(t['weak'])>=2 for t in rows)
    item=next(c for c in summary['cases']if c['id']==case['id']);checks['weak_primary_uncertain']=item['weak_primary_uncertain']
    out.append({'id':case['id'],'checks':checks,'pass':all(checks.values()),'traces':rows})
(D/'consumer-checks.json').write_text(json.dumps(out,indent=2));print(json.dumps([{'id':x['id'],'pass':x['pass'],'checks':x['checks']}for x in out],indent=2))
