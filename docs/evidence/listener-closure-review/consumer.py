# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,os
from .storage import connect
from .listener_query_display import query_diagnostic

def identity(row):return [row.get('id'),row.get('symbol_key'),row.get('file_path'),row.get('start_line'),row.get('end_line')]
def reorder(selected,project,query):
    with connect(project)as conn:diagnostic=query_diagnostic(conn,project,query)
    sources=[w['source']for w in diagnostic.get('checked_witnesses',[])]
    before=[identity(r)for r in selected]
    for row in selected:
        row.pop('listener_relation_weak',None)
        if any(all(row.get(k)==s[k]for k in ['symbol_key','file_path','source_digest','start_line','end_line'])for s in sources):row['listener_relation_weak']=True
    def tier(r):
        if (r.get('typed_contract_match')and not r.get('typed_contract_weak'))or any(r.get(k)for k in ['explicit_owner_identity_match','source_operation_match','target_owner_kind_match']):return 0
        return 1 if r.get('listener_relation_weak')else 2
    result=sorted(selected,key=tier)if sources else selected
    trace=os.environ.get('LISTENER_CONSUMER_TRACE')
    if trace:
        with open(trace,'a')as out:out.write(json.dumps({'query':query,'project':str(project.root),'before':before,'after':[identity(r)for r in result],'weak':[identity(r)for r in result if r.get('listener_relation_weak')],'association':diagnostic.get('status'),'qualifiers':diagnostic.get('unresolved_qualifiers')})+'\n')
    return result
