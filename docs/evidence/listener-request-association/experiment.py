# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Offline names only. Never imported by runtime, never marks a request satisfied."""
import json,re
from pathlib import Path
D=Path(__file__).resolve().parent
I=r'[A-Za-z_$][A-Za-z0-9_$]*'
GRAMMAR=re.compile(r'^(?:Find|Locate) the callable that binds (?P<source>'+I+r'(?:\s+'+I+r')*) callbacks to (?P<target>'+I+r'(?:\s+'+I+r')*) contract\.?$',re.I)
UNSUPPORTED={'not','no','never','without','except','excluding','avoid','rather','than','and','or','both','two','then','also','show','list','return','returns','locate','find','compare','include','caller','wrapper','declaration'}
def descriptor(query):
    if any(c in query for c in "'\"`\n\r"):
        return None
    match=GRAMMAR.fullmatch(query.strip())
    if match is None:return None
    source=match['source'].split();target=match['target'].split()
    if UNSUPPORTED & {t.casefold()for t in source+target}:return None
    if len(target)<2:return None
    type_name,member=target[-2:]
    if not re.fullmatch(r'[A-Z][A-Za-z0-9_$]*',type_name):return None
    if any(t[0].isupper()for t in target[:-2]):return None
    return {'relation':'callback-to-typed-parameter-member-name-association','type':type_name,'target_member':member,'unresolved_qualifiers':{'source_noun_phrase':match['source'],'target_noun_phrase_prefix':' '.join(target[:-2])},'relation_satisfied':False,'eligible_for_ranking':False,'relation_attachment_unresolved':True}

def segments(name):
    return [s for s in re.split(r'_+|(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])',name)if s]

def segment_match(selector,name):
    want=[s.casefold()for s in segments(selector)];have=[s.casefold()for s in segments(name)]
    return bool(want)and any(have[i:i+len(want)]==want for i in range(len(have)-len(want)+1))

def associate(desc,facts,coverage,dual):
    base={'property_selector_assumed':dual,'relation_attachment_unresolved':True,'relation_satisfied':False,'eligible_for_ranking':False,'global_uniqueness_claim':False,'coverage':coverage,'unresolved_qualifiers':desc['unresolved_qualifiers']if desc else{},'matched_identities':[]}
    if desc is None:return {**base,'status':'unsupported-descriptor'}
    candidates=[f for f in facts if f['declared_type']==desc['type']]
    selector=desc['target_member']
    exact=[f for f in candidates if f['member']==selector and(not dual or f['property']==selector)]
    matches=exact;lane='exact-name'
    if not matches:
        matches=[f for f in candidates if segment_match(selector,f['member'])and(not dual or segment_match(selector,f['property']))]
        lane='segment-uncertain'
        spellings={(f['property'],f['member'])if dual else f['member']for f in matches}
        if len(spellings)>1:return {**base,'status':'collision-unknown','collision_spellings':sorted(spellings)}
    if not matches:
        return {**base,'status':'domain-unknown'if coverage in {'partial','capped','old-index','saved-fixture-partial'}else'no-name-association'}
    ids=sorted({f['identity']for f in matches})
    return {**base,'status':lane+(':one-observed'if len(ids)==1 else':multiple-observed'),'matched_identities':ids,'observed_names':[{'property':f['property'],'member':f['member']}for f in matches]}

def main():
    p=json.loads((D/'protocol.json').read_text());out=[]
    for kind in ['controls','observations']:
        for c in p[kind]:
            desc=descriptor(c['query'])
            lanes={'target_member':associate(desc,c['facts'],c['coverage'],False),'dual_name_hypothesis':associate(desc,c['facts'],c['coverage'],True)}
            assertions={'never_satisfied':all(not x['relation_satisfied']for x in lanes.values()),'never_ranking_eligible':all(not x['eligible_for_ranking']for x in lanes.values()),'never_unique':all(not x['global_uniqueness_claim']for x in lanes.values())}
            expected=c['expected'];passed=all(assertions.values()) and(expected is None or all(lanes[k]['status']==v for k,v in expected.items()))
            out.append({'id':c['id'],'cohort':kind,'query':c['query'],'descriptor':desc,'lanes':lanes,'expected':expected,'safety_assertions':assertions,'pass':passed if expected is not None else None})
    (D/'results.json').write_text(json.dumps(out,indent=2))
    summary={'controls':len(p['controls']),'passed':sum(r['pass']is True for r in out),'failed':[r['id']for r in out if r['pass']is False],'observations':len(p['observations'])}
    (D/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
if __name__=='__main__':main()
