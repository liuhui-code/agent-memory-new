from pathlib import Path
import json,hashlib
O=Path(__file__).resolve().parent;cases=[]
for name in ('Bulletin','Invoice'):
 src=f'''@Component
export struct {name}Details {{
  title: string = ''
  subtitle: string = ''
  markup: string = ''

  build() {{
    Column() {{
      Text(this.title)
      Text(this.subtitle)
      Text(this.cleanedBody())
    }}
  }}

  cleanedBody(): string {{
    return this.markup
      .replace('<p>', '')
      .replace('</p>', '')
  }}
}}
'''
 log=f'''export class {name}DetailsStore {{
  title: string = ''
  saveDetails() {{
    this.title = this.title.trim()
    console.info('save {name.lower()} details markup title')
  }}
}}
'''
 cases.append(dict(id=name,sources={name+'Details.ets':src,name+'DetailsStore.ets':log},queries=[dict(id='original-style',query=f'{name} details still display markup tags. Locate the UI rendering cleanup owner rather than the {name.lower()} data entity.')]))
p=dict(classification='independent frozen synthetic Development; not actual incident or runtime causality',contract='Existing same-value static syntax witness can only add missing helper body without dropping logs, anchors, metadata, unknown sources or changing defaults; complete existing output is no-op; no public red means stop.',cases=cases)
s=json.dumps(p,indent=2);(O/'protocol.json').write_text(s);(O/'protocol.sha256').write_text(hashlib.sha256(s.encode()).hexdigest())
