# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,sys,subprocess,shutil,tempfile
from pathlib import Path
from install import install
from candidate import history_only
D=Path(__file__).resolve().parent;ROOT=D.parents[2]
def main():
    p=json.loads((D/'protocol.json').read_text());work=Path(tempfile.mkdtemp(prefix='history-symbol-trial-'));rt=work/'runtime';rt.mkdir();shutil.copytree(ROOT/'tools',rt/'tools');(rt/'EXPERIMENTAL_DISPOSABLE_RUNTIME').write_text('unvalidated one trial')
    project=work/'fixed';shutil.copytree(ROOT/p['sources_from'],project)
    def cli(project,*args):
        r=subprocess.run([sys.executable,str(rt/'tools/agent_memory.py'),*args,'--project',str(project),'--memory-home',str(work/(project.name+'-memory'))],capture_output=True,text=True)
        if r.returncode:raise RuntimeError(r.stderr)
        return json.loads(r.stdout)if '--json'in args else r.stdout
    cli(project,'init');cli(project,'learn-path','--path','.','--json');manager=work/'manager';manager.mkdir();cli(manager,'init');allout={}
    for phase in ['before','after']:
        if phase=='after':install(rt)
        out=[]
        for case in p['queries']:
            raw=cli(project,'context','--query',case['query'],'--json');compact=cli(project,'context','--query',case['query'],'--compact','--json');out.append({'case':case,'raw':raw,'compact':compact});(D/(phase+'.json')).write_text(json.dumps(out,indent=2))
        allout[phase]=out
        original=cli(manager,'eval-context-capability','--cases',str(ROOT/'docs/eval/system-capability-cases.json'),'--source',str(ROOT/'docs/eval/fixtures/system-capability'),'--case-id',p['original_scenario'],'--json');(D/(phase+'-original.json')).write_text(json.dumps(original,indent=2))
    summary=[]
    for b,a in zip(allout['before'],allout['after']):
        c=a['case'];bh=b['compact']['query_handoff'];ah=a['compact']['query_handoff'];omitted=history_only('load',c['query'])
        summary.append({'id':c['id'],'before_primary':bh['callable_evidence']['primary'],'after_primary':ah['callable_evidence']['primary'],'before_paths':[x['file_path']for x in bh['code_anchors']],'after_paths':[x['file_path']for x in ah['code_anchors']],'load_exact_omitted':omitted,'must_keep_exact_pass':not omitted if c.get('keep_exact') else None,'required_path_present':any(x['file_path']==c['required_path']for x in ah['code_anchors']),'budget':a['compact']['output_budget']})
    (D/'summary.json').write_text(json.dumps({'workspace':str(work),'results':summary},indent=2));print('fixed trial complete; rejection oracle remains unchanged')
if __name__=='__main__':main()
