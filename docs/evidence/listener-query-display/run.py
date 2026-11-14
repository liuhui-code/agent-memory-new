# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,sys,subprocess,shutil,tempfile
from pathlib import Path
from install_overlay import install
D=Path(__file__).resolve().parent;ROOT=D.parents[2];FIELD='experimental_listener_diagnostic'
def main():
    p=json.loads((D/'protocol.json').read_text());fixed=json.loads((ROOT/p['fixed_protocol_path']).read_text());work=Path(tempfile.mkdtemp(prefix='listener-query-display-'));rt=work/'runtime';rt.mkdir();shutil.copytree(ROOT/'tools',rt/'tools');(rt/'EXPERIMENTAL_DISPOSABLE_RUNTIME').write_text('docs-only')
    def cli(repo,project,*args):
        result=subprocess.run([sys.executable,str(repo/'tools/agent_memory.py'),*args,'--project',str(project),'--memory-home',str(work/(project.name+'-memory'))],text=True,capture_output=True)
        if result.returncode:raise RuntimeError(result.stderr)
        return json.loads(result.stdout)if '--json'in args else result.stdout
    def prepare(name,sources):
        project=work/name;project.mkdir()
        for path,text in sources.items():(project/path).write_text(text)
        cli(ROOT,project,'init');cli(ROOT,project,'learn-path','--path','.','--json');return project
    def context(repo,project,query,compact=False):return cli(repo,project,'context','--query',query,*(['--compact']if compact else[]),'--json')
    project=prepare('fixed',fixed['sources']);before=[]
    for c in fixed['queries']:before.append({'case':c,'raw':context(ROOT,project,c['query']),'compact':context(ROOT,project,c['query'],True)})
    (D/'before.json').write_text(json.dumps(before,indent=2));install(rt)
    old=context(rt,project,fixed['queries'][0]['query']);(D/'code-only.json').write_text(json.dumps(old,indent=2));assert old[FIELD]['matched_identities']==[]
    cli(rt,project,'learn-path','--path','.','--json');after=[];summary=[]
    for c,b in zip(fixed['queries'],before):
        raw=context(rt,project,c['query']);compact=context(rt,project,c['query'],True);same=context(ROOT,project,c['query']);diag=raw[FIELD]
        record={'case':c,'raw':raw,'compact':compact,'baseline_same_snapshot':same};after.append(record);(D/'after.json').write_text(json.dumps(after,indent=2))
        assert {k:v for k,v in raw.items()if k!=FIELD}==same
        assert FIELD not in compact
        oldh=b['compact']['query_handoff'];newh=compact['query_handoff']
        def anchors(h):return [{k:v for k,v in a.items()if k!='record_ids'}for a in h['code_anchors']]
        assert anchors(oldh)==anchors(newh)
        for k in ['file_path','symbol','source_range']:assert oldh['callable_evidence']['primary'].get(k)==newh['callable_evidence']['primary'].get(k)
        assert compact['output_budget']['estimated_tokens']<=1500
        size=len(json.dumps({FIELD:diag},ensure_ascii=False,indent=2).encode());assert size<=16384
        assert not any(diag[k]for k in ['relation_satisfied','eligible_for_ranking','global_uniqueness_claim'])
        summary.append({'query':c['query'],'association':diag['status'],'raw_same_snapshot_equal':True,'compact_anchors_primary_equal':True,'diagnostic_bytes':size,'budget':compact['output_budget'],'oracle_pass':{a['file_path']for a in newh['code_anchors']}=={c['expected']}and c['body']in json.dumps(newh['code_anchors'])})
    controls=[]
    for case in p['query_controls']:
        target=project
        if case['id']=='multiple':
            src=p['sources']['multiple-forwarders'];target=prepare('multiple',{src['file_path']:src['source']});cli(rt,target,'learn-path','--path','.','--json')
        out=context(rt,target,case['query']);controls.append({'id':case['id'],'output':out,'expected':case['expected'],'pass':out[FIELD]['status']==case['expected']});(D/'controls.json').write_text(json.dumps(controls,indent=2))
    src=p['sources']['native'];native=prepare('native',{src['file_path']:src['source']});cli(rt,native,'learn-path','--path','.','--json');out=context(rt,native,p['native_query']);(D/'native-observation.json').write_text(json.dumps(out,indent=2))
    source=project/'Relay.ets';content=source.read_bytes()
    try:
        source.write_bytes(content+b'\n// stale\n');out=context(rt,project,fixed['queries'][0]['query']);(D/'stale.json').write_text(json.dumps(out,indent=2));assert out[FIELD]['matched_identities']==[]
    finally:source.write_bytes(content)
    (D/'summary.json').write_text(json.dumps({'queries':summary,'controls':[{'id':x['id'],'pass':x['pass']}for x in controls],'native_observation':json.loads((D/'native-observation.json').read_text())[FIELD]['status'],'stale_unknown':True,'workspace':str(work)},indent=2));print(json.dumps({'controls_passed':sum(x['pass']for x in controls),'workspace':str(work)}))
if __name__=='__main__':main()
