import json,hashlib
from pathlib import Path
O=Path(__file__).resolve().parent
cases=[]
for noun in ['Bulletin','Invoice']:
 sources={f'{noun}Record.ets':f"export class {noun}Record {{\n  body: string = ''\n}}\n",f'{noun}Panel.ets':f"@Component\nexport struct {noun}Panel {{\n  body: string = ''\n  cleanBody(): string {{\n    return this.body.replace('<p>', '').replace('</p>', '')\n  }}\n  build() {{\n    Column() {{ Text(this.cleanBody()) }}\n  }}\n}}\n",f'{noun}RecordPreview.ets':f"@Component\nexport struct {noun}RecordPreview {{\n  body: string = ''\n  build() {{\n    Column() {{ Text(this.body) }}\n  }}\n}}\n"}
 queries=[{'id':'render-rather-role','query':f'{noun} details still display markup tags. Locate the UI rendering cleanup owner rather than the {noun.lower()} data entity.'}, {'id':'render-positive','query':f'{noun} details still display markup tags. Locate the UI rendering cleanup owner.'},{'id':'render-rather-named','query':f'Locate {noun}Panel.cleanBody rather than {noun}Record.'},{'id':'entity-reverse','query':f'Locate the {noun}Record data entity rather than the {noun}Panel rendering owner.'},{'id':'compare-control','query':f'Compare {noun}Record and {noun}Panel source.'}]
 cases.append(dict(id=noun,sources=sources,queries=queries))
p={'classification':'frozen independent synthetic Development, not external efficacy','hypothesis':'Rather-than result clause may negate positive rendering target or promote excluded entity; near-name UI and reverse explicit data request must not be treated as same entity. No expected exact ranking or imposed sole-owner rule.','stop':'If original-style request preserves cleanup target and excludes entity, do not expand rules merely for variant scores. Do not mutate these queries after observing results.','cases':cases}
s=json.dumps(p,ensure_ascii=False,indent=2);(O/'protocol.json').write_text(s);(O/'protocol.sha256').write_text(hashlib.sha256(s.encode()).hexdigest()+'\n')
