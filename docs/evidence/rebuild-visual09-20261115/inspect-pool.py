# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,sys,tempfile,shutil
from pathlib import Path
D=Path(__file__).resolve().parent;ROOT=D.parents[2];sys.path.insert(0,str(ROOT))
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.storage import resolve_project
from tools.agent_memory_runtime.query_results import _context_pass
from tools.agent_memory_runtime.query_collect import collect_matches_with_audit
from tools.agent_memory_runtime.query_render_selection import bind_render_context
q='库存分类选择区遮挡数量输入控件，请定位负责层叠背景的 ArkTS 视图。';b=AgentMemoryTestBase()
with tempfile.TemporaryDirectory()as t:
 root=Path(t)/'project';shutil.copytree(ROOT/'docs/eval/fixtures/system-capability',root)
 b.run_memory(root,'init');b.run_memory(root,'learn-path','--path','.','--json');p=resolve_project(str(root),str(b.memory_home(root)))
 base=_context_pass(p,q);trial=_context_pass(p,q,allow_render_recall=True)
 col=collect_matches_with_audit(p,q,allow_render_recall=True)
 r={'pool':col.matches['wiki_matches'],'baseline':base,'trial':trial,'bound_type':type(bind_render_context(p,q,base,trial)).__name__}
 (D/'pool-inspection.json').write_text(json.dumps(r,ensure_ascii=False,indent=2))
 print('trial',[(x.get('kind'),x.get('file_path'),x.get('symbol'))for x in trial['wiki_matches']]);print('bound',r['bound_type'])
