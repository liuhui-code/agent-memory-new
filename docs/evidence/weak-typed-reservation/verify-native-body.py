# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json
from pathlib import Path
p=Path(__file__).parent
source=Path('docs/eval/fixtures/system-capability/.benchmark-fixtures/evidence-funnel/src/adapters/NativeResultBoundary.ets').read_text().splitlines()
expected='\n'.join(source[6:16])
for label,out in json.loads((p/'native-operation-final.json').read_text()).items():
    compact=out['compact']
    anchor=next(a for a in compact['query_handoff']['code_anchors'] if a['file_path'].endswith('NativeResultBoundary.ets'))
    excerpt=next(e for e in anchor['source_excerpts'] if e['start_line']==7 and e['end_line']==16)
    assert excerpt['content']==expected and not excerpt['truncated']
    assert compact['output_budget']['estimated_tokens']<=1500
    print(label, 'exact source 7–16 retained; budget',compact['output_budget']['estimated_tokens'])
