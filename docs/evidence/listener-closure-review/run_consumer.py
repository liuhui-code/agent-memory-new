# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,sys,subprocess,shutil,tempfile,os,importlib.util
from pathlib import Path
from install_consumer import install as consumer
D=Path(__file__).resolve().parent;ROOT=D.parents[2]
def main():
    work=Path(tempfile.mkdtemp(prefix='listener-closure-'));rt=work/'runtime';rt.mkdir();shutil.copytree(ROOT/'tools',rt/'tools');(rt/'EXPERIMENTAL_DISPOSABLE_RUNTIME').write_text('experiment')
    spec=importlib.util.spec_from_file_location('qd',ROOT/'docs/evidence/listener-query-display/install_overlay.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.install(rt)
    protocol=json.loads((D/'consumer-protocol.json').read_text());fixed=json.loads((ROOT/protocol['fixed_five']).read_text());trace=D/'consumer-trace.jsonl'
    def cli(project,*args,phase='before'):
        r=subprocess.run([sys.executable,str(rt/'tools/agent_memory.py'),*args,'--project',str(project),'--memory-home',str(work/(project.name+'-memory'))],capture_output=True,text=True,env={**os.environ,'LISTENER_CONSUMER_TRACE':str(trace)})
        if r.returncode:raise RuntimeError(json.dumps({'args':args,'stderr':r.stderr,'stdout':r.stdout}))
        return json.loads(r.stdout)if '--json'in args else r.stdout
    def prepare(name,sources):
        project=work/name;project.mkdir()
        for path,source in sources.items():(project/path).write_text(source)
        cli(project,'init');cli(project,'learn-path','--path','.','--json');return project
    projects={'fixed':prepare('fixed',fixed['sources'])}
    for c in protocol['controls']:projects[c['id']]=prepare(c['id'],c['sources'])
    manager=work/'original-manager';manager.mkdir();cli(manager,'init')
    cases=[{'id':'fixed-'+str(i),'project':'fixed','query':c['query'],'oracle':c}for i,c in enumerate(fixed['queries'])]+[{'id':c['id'],'project':c['id'],'query':c['query'],'oracle':c.get('safety_oracle')}for c in protocol['controls']]
    outputs={}
    for phase in ['before','after']:
        if phase=='after':consumer(rt)
        stage=[]
        for c in cases:
            project=projects[c['project']];raw=cli(project,'context','--query',c['query'],'--json');compact=cli(project,'context','--query',c['query'],'--compact','--json');stage.append({'case':c,'raw':raw,'compact':compact});(D/(phase+'-consumer.json')).write_text(json.dumps(stage,indent=2))
        result=cli(manager,'eval-context-capability','--cases',str(ROOT/'docs/eval/system-capability-cases.json'),'--source',str(ROOT/'docs/eval/fixtures/system-capability'),'--case-id',protocol['original_case_id'],'--json')
        (D/(phase+'-native.json')).write_text(json.dumps(result,indent=2));outputs[phase]=stage
    summary=[]
    for b,a in zip(outputs['before'],outputs['after']):
        bh=b['compact']['query_handoff'];ah=a['compact']['query_handoff'];weak=ah['callable_evidence']['primary'].get('listener_relation_weak',False)
        summary.append({'id':a['case']['id'],'before_primary':bh['callable_evidence']['primary'],'after_primary':ah['callable_evidence']['primary'],'after_certainty':ah['callable_evidence']['certainty'],'weak_primary_uncertain':not weak or ah['callable_evidence']['certainty']=='uncertain','before_paths':[r['file_path']for r in bh['code_anchors']],'after_paths':[r['file_path']for r in ah['code_anchors']],'budget':a['compact']['output_budget']})
    (D/'consumer-summary.json').write_text(json.dumps({'workspace':str(work),'cases':summary},indent=2));print('one fixed candidate complete')
if __name__=='__main__':main()
