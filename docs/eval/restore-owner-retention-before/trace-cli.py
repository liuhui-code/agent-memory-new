# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json, os, runpy, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
sys.path.insert(0, str(Path.cwd() / 'tools'))
rows = []
names = {'focus_callable_anchors', 'admitted_log_owners', 'collect_graph_neighbor_matches'}
def trace(frame, event, arg):
    name = frame.f_code.co_name
    if name not in names:
        return
    if event == 'return':
        keys = ('anchors', 'evidence', 'path_activated', 'query', 'wiki', 'logs')
        rows.append({'function': name, 'event': event, 'input': {k:frame.f_locals.get(k) for k in keys}, 'result':arg})
    elif event == 'line' and name == 'focus_callable_anchors':
        rows.append({'function': name, 'event': event, 'line': frame.f_lineno})
    return trace
sys.settrace(trace)
try:
    runpy.run_path('tools/agent_memory.py', run_name='__main__')
finally:
    sys.settrace(None)
    Path(os.environ['TRACE_FILE']).write_text(json.dumps(rows, indent=2, default=str))
