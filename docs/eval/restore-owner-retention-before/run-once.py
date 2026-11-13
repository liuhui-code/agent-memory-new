# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json, os, subprocess, sys, tempfile
from pathlib import Path
root = Path(__file__).resolve().parent
protocol = json.loads((root/'protocol.json').read_text())
assert not (root/'execution-started').exists(), 'Frozen single execution already started'
(root/'execution-started').write_text('Single five-query raw/compact execution; do not rerun.\n')
results = []
with tempfile.TemporaryDirectory() as directory:
    project = Path(directory)/'source'; project.mkdir()
    memory = Path(directory)/'memory'
    for name, content in protocol['sources'].items():
        (project/name).write_text(content)
    def call(args, trace=None):
        entry = root/'trace-cli.py' if trace else Path('tools/agent_memory.py')
        env = dict(os.environ)
        if trace: env['TRACE_FILE'] = str(root/trace)
        command = [sys.executable,str(entry),*args,'--project',str(project),'--memory-home',str(memory)]
        result = subprocess.run(command,capture_output=True,text=True,env=env)
        return {'command':command,'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr}
    setup = [call(['init']),call(['learn-path','--path','.','--json'])]
    (root/'setup.json').write_text(json.dumps(setup,indent=2))
    assert all(row['returncode']==0 for row in setup), 'Setup failed; stop'
    for case in protocol['queries']:
        row = {'case':case}
        for mode in ['raw','compact']:
            row[mode] = call(['context','--query',case['query'],*(['--compact'] if mode=='compact' else []),'--json'],case['id']+'-'+mode+'-trace.json')
        results.append(row)
        (root/'public-before.json').write_text(json.dumps(results,indent=2))
