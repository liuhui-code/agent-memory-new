# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json, sys, tempfile, time
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path.cwd()))
from tools.agent_memory_runtime import semantic_ecma
from tools.agent_memory_runtime.storage import resolve_project
source='\n'.join('class Panel%d {\n @State private live: boolean = false\n note: string = "@State ghost"\n read(): boolean { return this.live }\n}'%i for i in range(100))
with tempfile.TemporaryDirectory() as d:
 project=resolve_project(d); path=Path(d)/'Panels.ets'
 with patch.object(semantic_ecma,'callback_mask_lines',wraps=semantic_ecma.callback_mask_lines) as masked:
  start=time.perf_counter(); parsed=semantic_ecma.parse_source(project,path,source,'ArkTS',True); elapsed=time.perf_counter()-start
  result={'source_bytes':len(source.encode()),'containers':100,'semantic_mask_calls':masked.call_count,'states':len([s for s in parsed.entities if s.kind=='state']),'elapsed_seconds':elapsed,'claim':'bounded local smoke measurement, not throughput benchmark'}
Path('docs/eval/state-declaration-lexical/mask-cost.json').write_text(json.dumps(result,indent=2))
print(result)
