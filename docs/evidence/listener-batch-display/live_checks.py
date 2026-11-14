# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Post-learn diagnostic and optional fault isolation; no source/query alteration."""
import json,subprocess,sys,os
from pathlib import Path
D=Path(__file__).resolve().parent
state=json.loads((D/'workspace.json').read_text());work=Path(state['workspace']);rt=Path(state['candidate']);project=work/'fixed'
def cli(*args,mode=''):
    p=subprocess.run([sys.executable,str(rt/'tools/agent_memory.py'),*args,'--project',str(project),'--memory-home',str(work/'fixed-memory')],capture_output=True,text=True,env={**os.environ,'LISTENER_TEST_FAULT':mode})
    if p.returncode:raise RuntimeError(p.stderr)
    return json.loads(p.stdout)
def rows():return cli('list','--type','code-symbol','--limit','300','--json')
def actual(r):return next(x for x in r if x['symbol']=='connect')
results=[];before=rows();source=project/'Relay.ets';original=source.read_bytes()
try:
    source.write_bytes(original+b'\n// changed snapshot\n');stale=rows();assert actual(stale)['experimental_listener_diagnostic']['status']=='unknown'
    source.unlink();missing=rows();assert actual(missing)['experimental_listener_diagnostic']['status']=='unknown'
finally:source.write_bytes(original)
results.extend([{'id':'actual-cli-stale','pass':True},{'id':'actual-cli-missing','pass':True}])
# Fault injection at optional producer return; actual legacy adapter/index/CLI run.
p=rt/'tools/agent_memory_runtime/listener_experiment_support.py';old=p.read_text()
hook='''\n    import os,copy\n    mode=os.environ.get('LISTENER_TEST_FAULT')\n    if mode=='duplicate':out=out+copy.deepcopy(out)\n    elif mode=='overcount' and out:out=[out[0]]*65\n    elif mode=='conflict' and out:\n        bad=copy.deepcopy(out[0]);bad['invocation']['member']='conflictingMember';out.append(bad)\n    return out'''
assert old.count('    return out')==1;p.write_text(old.replace('    return out',hook))
observations=[]
try:
    for mode,count in [('duplicate',2),('overcount',0),('conflict',0)]:
        learned=cli('learn-path','--path','.','--json',mode=mode);after=rows()
        oldmap={x['symbol_key']:x for x in before};newmap={x['symbol_key']:x for x in after};assert oldmap.keys()==newmap.keys()
        for key in oldmap:
            for field in ['mechanism_evidence','signature','source_digest','start_line','end_line','symbol_type']:
                assert oldmap[key][field]==newmap[key][field],(mode,key,field)
        facts=json.loads(actual(after).get('typed_invocation_witnesses')or'[]');assert len(facts)==count,(mode,len(facts))
        observations.append({'mode':mode,'learn':learned,'rows':after,'pass':True})
finally:p.write_text(old)
cli('learn-path','--path','.','--json')
(D/'live-checks.json').write_text(json.dumps({'source_status':results,'optional_faults':observations},indent=2))
print('2 actual CLI source checks and 3 actual learn/index fault checks passed')
