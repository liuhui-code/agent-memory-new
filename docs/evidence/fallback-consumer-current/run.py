# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json, os, subprocess, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from tools.agent_memory_runtime.benchmark_workspace import materialized_workspace
D = Path(__file__).parent.resolve()
p = json.loads((D / 'protocol.json').read_text())
with tempfile.TemporaryDirectory() as tmp, materialized_workspace(Path(p['source_root']).resolve(), p['original_case']) as root:
    def run(label, *args):
        r = subprocess.run([sys.executable, str(D / 'trace-cli.py'), *args, '--project', str(root), '--memory-home', tmp + '/memory'], text=True, capture_output=True, check=True, env=dict(os.environ, TRACE_FILE=str(D / (label + '-trace.json'))))
        return json.loads(r.stdout) if '--json' in args else r.stdout
    run('init', 'init')
    run('learn', 'learn-path', '--path', '.')
    out = {mode: run(mode, 'context', '--query', p['query']['description'], *(['--compact'] if mode == 'compact' else []), '--json') for mode in ('raw', 'compact')}
    out['symbols'] = run('symbols', 'list', '--type', 'code-symbol', '--limit', '2000', '--json')
    out['edges'] = run('edges', 'list', '--type', 'code-edge', '--limit', '3000', '--json')
    (D / 'public.json').write_text(json.dumps(out, indent=2) + '\n')
