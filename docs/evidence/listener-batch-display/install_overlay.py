# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import importlib.util,shutil
from pathlib import Path
D=Path(__file__).resolve().parent;ROOT=D.parents[2]
def install(target):
    spec=importlib.util.spec_from_file_location('v2install',D.parent/'listener-model-v2/install_overlay.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.install(target)
    rt=Path(target)/'tools/agent_memory_runtime'
    for src,dst in [('batch_support.py','listener_batch_support.py'),('display.py','listener_display.py')]:shutil.copy2(D/src,rt/dst)
    p=rt/'semantic_models.py';s=p.read_text();a=s.index('        from .listener_experiment_support import validate');b=s.index('        self.capabilities',a)
    s=s[:a]+'        from .listener_batch_support import optional_batch\n        self.typed_invocation_witnesses = optional_batch(self.typed_invocation_witnesses, entities_by_key, self.source_digests)\n'+s[b:]
    s=s.replace('optional_object_list(value.get("typed_invocation_witnesses"), "typed_invocation_witnesses")','value.get("typed_invocation_witnesses", [])');p.write_text(s)
    p=rt/'command_handlers.py';s=p.read_text();old='    output([row_dict(row) for row in rows], args.json)';a=s.index(old,s.index('def list_records('));s=s[:a]+s[a:].replace(old,'    records = [row_dict(row) for row in rows]\n    if args.type == "code-symbol":\n        from .listener_display import display\n        records = display(records, project.root)\n    output(records, args.json)',1);p.write_text(s)
