# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import hashlib, json, pathlib, shutil, subprocess, sys, tempfile
repo = pathlib.Path(__file__).resolve().parents[3]
fixture = repo / 'tests/fixtures/rebuilt-sink-literal'
case = next(c for c in json.loads((fixture/'manifest.json').read_text())['cases'] if c['id']=='second_message_parameter')
out=pathlib.Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=False)
source=fixture/case['source']
assert hashlib.sha256(source.read_bytes()).hexdigest()==case['source_sha256']
with tempfile.TemporaryDirectory() as temp:
    project=pathlib.Path(temp); shutil.copy(source, project/source.name)
    commands=[('execute',['node',str(project/source.name)])]
    cli=[sys.executable,'-B',str(repo/'tools/agent_memory.py')]
    commands += [(stage,cli+[command,'--project',str(project),*extra]) for stage, command, extra in [('init','init',[]),('index','wiki-index',[]),('raw','context',['--query',case['query'],'--json']),('compact','context',['--query',case['query'],'--compact','--json'])]]
    result={}
    for stage,args in commands:
        p=subprocess.run(args,text=True,capture_output=True)
        (out/(stage+'.stdout')).write_text(p.stdout); (out/(stage+'.stderr')).write_text(p.stderr)
        assert p.returncode==0,(stage,p.stderr)
        if stage=='execute': result['actual_stdout']=p.stdout
        if stage in ('raw','compact'):
            handoff=json.loads(p.stdout)['query_handoff']
            anchors=[a for a in handoff['log_anchors'] if a.get('function')=='run' and a.get('evidence_class')=='static_wrapped']
            result[stage]=anchors
    result['source_sha256']=case['source_sha256'];result['expected']=case['expected_effect_static_template']
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result,indent=2))
