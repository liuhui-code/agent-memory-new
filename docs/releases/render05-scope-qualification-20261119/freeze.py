from pathlib import Path
import json
O=Path(__file__).resolve().parent
cases=[]
for topic,record,panel,field in [('收据','ReceiptRecord','ReceiptPanel','body'),('通知','NoticeRecord','NoticePanel','text')]:
 def ui(name):return f"@Component\nexport struct {name} {{\n  {field}: string = ''\n  build() {{\n    Column() {{ Text(this.cleanBody()) }}\n  }}\n  cleanBody(): string {{\n    return this.{field}.replace('<p>', '').replace('</p>', '')\n  }}\n}}\n"
 sources={f'{record}.ets':f"export class {record} {{\n  {field}: string = ''\n}}\n",f'{panel}.ets':ui(panel),f'{record}Preview.ets':ui(record+'Preview'),'Settings.ets':"export class Settings {\n  label: string = ''\n  save(): void { this.label = this.label.trim() }\n}\n"}
 base=f'{topic}详情仍显示 HTML 标签，请定位清洗并渲染正文的 view'
 cases.append(dict(id=record,sources=sources,queries=[dict(id='exact-data-exclusion',query=base+f'，不要返回 {record} 数据类。',required_complete_owners=[panel,record+'Preview']),dict(id='positive',query=base+'。',required_complete_owners=[panel,record+'Preview']),dict(id='contradictory-ui-exclusion',query=base+f'，不要返回 {panel} 数据类。',require_baseline_unchanged=True)]))
(O/'protocol.json').write_text(json.dumps(dict(classification='prospective independent Development capability qualification; no runtime changes yet',contract='Single explicit excluded data class identity, not owner/path substring. Both genuine cleanup UI owners including near-name retained. Existing log/graph/budget and uncertain identity fail open to baseline.',cases=cases,additional_required_controls=['same short class identity in different directories','unknown class','duplicate UI/class name','explicit positive and excluded same target','quoted/log requests','multiple exclusion identifiers','old identity/digest/index generation and budget rollback']),ensure_ascii=False,indent=2))
