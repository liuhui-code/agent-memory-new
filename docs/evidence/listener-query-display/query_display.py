# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json
from .listener_display import diagnose
from .listener_name_association import descriptor,associate
FIELD='experimental_listener_diagnostic'
def unknown(status):
    return {'status':status,'coverage':'partial','relation_satisfied':False,'eligible_for_ranking':False,'global_uniqueness_claim':False,'unresolved_qualifiers':['request not established']}
def envelope_size(value):return len(json.dumps({FIELD:value},ensure_ascii=False,indent=2).encode())
def query_diagnostic(conn,project,query):
    desc=descriptor(query);names=[];witnesses={};states={}
    if desc is None:return {**unknown('unsupported-descriptor'),'descriptor':None}
    rows=conn.execute('SELECT * FROM code_symbols WHERE project_id=? ORDER BY id ASC LIMIT 64',(project.project_id,)).fetchall()
    for raw in rows:
        row=dict(raw);d=diagnose(row,project.root);status=d['status'];states[status]=states.get(status,0)+1
        if status!='current-source-slices-checked':continue
        for w in d['facts']:
            identity=json.dumps([w['source']['symbol_key'],w['source']['source_digest'],w['invocation']['range']],separators=(',',':'))
            witnesses[identity]=w
            names.append({'identity':identity,'declared_type':w['formal']['declared_type'],'property':w['callback']['property'],'member':w['invocation']['member']})
    if len(names)>64:return unknown('unknown-cap')
    association=associate(desc,names,'partial',False)
    out={**association,'descriptor':desc,'source_states':states,'checked_witnesses':[witnesses[k]for k in association['matched_identities']],'source_validation':'supported-slices-not-full-owner-authentication'}
    if envelope_size(out)>16384:return unknown('unknown-cap')
    return out
