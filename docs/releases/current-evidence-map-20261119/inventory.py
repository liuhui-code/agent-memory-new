from pathlib import Path
import json,collections
R=Path(__file__).resolve().parent.parent/'repo';hist=json.loads((R.parent.parent/'resume-verified-20261109/remaining74-final-clustering-20261109/CASE_MAPPING.json').read_text());ids=list(dict.fromkeys(c['case_id'].split('::')[0]for c in hist));out={i:[]for i in ids}
for root in ('docs/evidence','docs/releases','docs/eval'):
 for p in (R/root).rglob('*.json'):
  try:
   if p.stat().st_size>15_000_000:continue
   x=json.loads(p.read_text())
   if not isinstance(x,dict)or x.get('schema_version')!='agent-context-capability-result/v1':continue
   groups=collections.defaultdict(list)
   for c in x.get('cases',[]):
    if c.get('scenario_id')in out:groups[c['scenario_id']].append(c)
   for k,v in groups.items():out[k].append(dict(path=str(p.relative_to(R)),date=x.get('recorded_at'),passed=sum(c.get('status')=='pass'for c in v),total=len(v),variants=[c['case_id']for c in v]))
  except (ValueError,OSError):pass
for k in out:out[k].sort(key=lambda r:str(r['date']),reverse=True)
O=Path(__file__).resolve().parent;(O/'all-results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
for k,v in out.items():
 print(k)
 for r in v[:3]:print(' ',r['date'],f"{r['passed']}/{r['total']}",r['path'])
