# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json, os, shutil, subprocess, tempfile
from pathlib import Path
D = Path(__file__).parent.resolve()
p = json.loads((D / 'protocol.json').read_text())
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp) / 'source'
    shutil.copytree(D / 'source', root)
    def run(label, *args):
        result = subprocess.run(['python', str(D / 'trace-cli.py'), *args, '--project', str(root), '--memory-home', tmp + '/memory'], text=True, capture_output=True, check=True, env=dict(os.environ, TRACE_FILE=str(D / (label + '-trace.json'))))
        return json.loads(result.stdout) if '--json' in args else result.stdout
    run('init', 'init')
    run('learn', 'learn-path', '--path', '.')
    out = []
    for q in p['queries']:
        out.append({'case': q, 'raw': run(q['id'] + '-raw', 'context', '--query', q['query'], '--json'), 'compact': run(q['id'] + '-compact', 'context', '--query', q['query'], '--compact', '--json')})
    (D / 'public.json').write_text(json.dumps(out, indent=2) + '\n')
