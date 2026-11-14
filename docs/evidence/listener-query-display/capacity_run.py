# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,sys,subprocess,tempfile,shutil
from pathlib import Path
from install_overlay import install
D=Path(__file__).resolve().parent;ROOT=D.parents[2];FIELD='experimental_listener_diagnostic'
def main():
    p=json.loads((D/'capacity-protocol.json').read_text());work=Path(tempfile.mkdtemp(prefix='listener-query-cap-'));rt=work/'runtime';rt.mkdir();shutil.copytree(ROOT/'tools',rt/'tools');(rt/'EXPERIMENTAL_DISPOSABLE_RUNTIME').write_text('experimental');install(rt)
    sys.path.insert(0,str(rt));from tools.agent_memory_runtime.listener_name_association import descriptor,associate
    def cli(repo,project,*args):
        r=subprocess.run([sys.executable,str(repo/'tools/agent_memory.py'),*args,'--project',str(project),'--memory-home',str(work/(project.name+'-memory'))],capture_output=True,text=True)
        if r.returncode:raise RuntimeError(r.stderr)
        return json.loads(r.stdout)if '--json'in args else r.stdout
    results=[]
    for case in p['cases']:
        project=work/case['id'];project.mkdir()
        for name,source in case['sources'].items():(project/name).write_text(source)
        cli(rt,project,'init')
        for name in case['sources']:cli(rt,project,'learn-path','--path',name,'--json')
        rows=cli(rt,project,'list','--type','code-symbol','--limit','300','--json')
        # SQL query scans ascending IDs; list order is reverse. Restrict same64.
        scanned=sorted(rows,key=lambda r:r['id'])[:64];facts=[];witnesses={};states={}
        for row in scanned:
            d=row.get('experimental_listener_diagnostic',{});states[d.get('status','unknown')]=states.get(d.get('status','unknown'),0)+1
            if d.get('status')!='current-source-slices-checked':continue
            for w in d['facts']:
                identity=json.dumps([w['source']['symbol_key'],w['source']['source_digest'],w['invocation']['range']],separators=(',',':'));witnesses[identity]=w
                facts.append({'identity':identity,'declared_type':w['formal']['declared_type'],'property':w['callback']['property'],'member':w['invocation']['member']})
        desc=descriptor(p['query']);a=associate(desc,facts,'partial',False);hyp={**a,'descriptor':desc,'source_states':states,'checked_witnesses':[witnesses[k]for k in a['matched_identities']],'source_validation':'supported-slices-not-full-owner-authentication'}
        size=len(json.dumps({FIELD:hyp},ensure_ascii=False,indent=2).encode())
        raw=cli(rt,project,'context','--query',p['query'],'--json');old=cli(ROOT,project,'context','--query',p['query'],'--json');compact=cli(rt,project,'context','--query',p['query'],'--compact','--json');oldcompact=cli(ROOT,project,'context','--query',p['query'],'--compact','--json')
        d=raw[FIELD];checks={'unknown_cap':d['status']=='unknown-cap','partial':d['coverage']=='partial','false_authority':not any(d[k]for k in ['relation_satisfied','eligible_for_ranking','global_uniqueness_claim']),'raw_equal':{k:v for k,v in raw.items()if k!=FIELD}==old,'compact_equal':compact==oldcompact,'compact_no_diagnostic':FIELD not in compact,'compact_budget':compact['output_budget']['estimated_tokens']<=1500,'intended_branch':len(facts)>64 if case['id']=='fact-cap' else len(facts)<=64 and size>16384}
        results.append({'id':case['id'],'checks':checks,'pass':all(checks.values()),'checked_facts':len(facts),'scanned_rows':len(scanned),'hypothetical_envelope_bytes':size,'actual_envelope_bytes':len(json.dumps({FIELD:d},ensure_ascii=False,indent=2).encode()),'rows':rows,'raw':raw,'baseline_raw':old,'compact':compact,'baseline_compact':oldcompact})
        (D/'capacity-results.json').write_text(json.dumps(results,indent=2))
    print(json.dumps({'workspace':str(work),'results':[{k:c[k]for k in ['id','pass','checks','checked_facts','hypothetical_envelope_bytes']}for c in results]},indent=2))
if __name__=='__main__':main()
