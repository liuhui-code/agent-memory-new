# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import dataclasses,hashlib,json,sys
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from tools.agent_memory_runtime.semantic_ecma import parse_source
from tools.agent_memory_runtime.source_call_scanner import scan_calls_masked,code_mask
base=ROOT/'docs/eval/fixtures/system-capability';out={}
for relative in ('src/views/BoardGestureSurface.ets','src/views/CanvasInteractionSurface.ets','src/models/InteractionState.ets'):
 path=base/relative;raw=path.read_bytes();text=raw.decode();parsed=parse_source(SimpleNamespace(root=base),path,raw,'ArkTS',True)
 out[relative]={'source':text,'sha256':hashlib.sha256(raw).hexdigest(),'entities':[dataclasses.asdict(x) for x in parsed.entities],'relations':[dataclasses.asdict(x) for x in parsed.relations],'mechanisms':[dataclasses.asdict(x) for x in parsed.mechanisms],'gaps':parsed.gaps,'balanced_calls':scan_calls_masked(text,code_mask(text),r'\b(?:this\.)?[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*\s*\(')}
(Path(__file__).parent/'source-observation.json').write_text(json.dumps(out,indent=2))
