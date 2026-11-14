# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,hashlib
from .context_source_excerpt import safe_source_path
from .semantic_models import SemanticEntity
from .listener_experiment_support import validate
from .listener_experiment_prototype import validate_witness
from .listener_batch_support import normalize

def diagnose(row,root):
    out={'status':'unknown','coverage':'bounded-record-not-global','cap_status':'optional-may-be-omitted','relation_satisfied':False,'eligible_for_ranking':False,'unresolved_qualifiers':['request not evaluated'],'facts':[]}
    try:
        raw=row.get('typed_invocation_witnesses')
        if not raw:return out
        facts=normalize(json.loads(raw))
        if not facts:return out
        path=safe_source_path(root.resolve(),row.get('file_path'))
        if path is None:return out
        with path.open('rb') as stream: data=stream.read(32769)
        if len(data)>32768:return out
        digest=hashlib.sha256(data).hexdigest()
        if digest!=row.get('source_digest'):return out
        text=data.decode('utf-8')
        e=SemanticEntity(key=row['symbol_key'],file_path=row['file_path'],name=row['symbol'],kind=row['symbol_type'],qualified_name=row['qualified_name'],signature=row['signature'],start_line=row['start_line'],end_line=row['end_line'])
        if e.kind not in {'function','method'}:return out
        for w in facts:
            validate(w,e,{e.file_path:digest})
            validate_witness(w,{'source':text,'file_path':e.file_path,'sha256':digest})
        out.update(status='current-source-slices-checked',facts=facts)
    except (ValueError,TypeError,KeyError,OSError,AssertionError):pass
    return out

def display(rows,root):
    used=2
    for row in rows[:64]:
        d=diagnose(row,root);size=len(json.dumps(d,ensure_ascii=False).encode())
        if size>4096: d={'status':'unknown-diagnostic-cap'};size=len(json.dumps(d).encode())
        if used+size+2>65536:break
        row['experimental_listener_diagnostic']=d;used+=size+2
    return rows
