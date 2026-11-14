# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import importlib.util,shutil
from pathlib import Path
D=Path(__file__).resolve().parent;ROOT=D.parents[2]
def install(target):
    spec=importlib.util.spec_from_file_location('previous_install',D.parent/'listener-batch-display/install_overlay.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.install(target)
    rt=Path(target)/'tools/agent_memory_runtime'
    shutil.copy2(D/'query_display.py',rt/'listener_query_display.py')
    shutil.copy2(D.parent/'listener-request-association/experiment.py',rt/'listener_name_association.py')
    p=rt/'command_handlers.py';s=p.read_text();start=s.index('def context(');end=s.index('\ndef ',start+4);part=s[start:end]
    old='    output(data, args.json)';assert part.count(old)==1
    part=part.replace(old,'    if not args.compact:\n        from .listener_query_display import query_diagnostic\n        with connect(project) as conn:\n            data["experimental_listener_diagnostic"] = query_diagnostic(conn, project, args.query)\n'+old)
    p.write_text(s[:start]+part+s[end:])
