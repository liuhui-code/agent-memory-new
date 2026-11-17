"""Source-only SQL and UI slot witnesses; no database or output authority."""
import re
from .sql_slot_source_inventory import inventory_source, authenticated, Unknown, compact, span, pairs, legal_binding

from .sql_slot_source_objects import sql_result, ui_element, render_pattern

IDENT = r'[A-Za-z_$][A-Za-z0-9_$]*'


def classify_sql_owner(source, owner, M, sql_kind='SQL'):
    try:
        authenticated(source, owner)
        if sql_kind not in ('SQL', 'LIKE') or not re.fullmatch(IDENT, M): raise Unknown('request')
        methods = [m for m in owner['methods'] if m['name']==M]
        if not methods: return dict(status='known', matches=[])
        matches=[]
        for method in methods:
            param=re.fullmatch('('+IDENT+'):string',method['parameters'])
            b=method['_body']
            if not param or len(b)<4 or [t.value for t in b[:1]]!=['const'] or b[2].value!='=' or b[3].kind!='string': raise Unknown('sql_prefix')
            if not legal_binding(param[1]) or b[1].kind!='ident' or not legal_binding(b[1].value): raise Unknown('sql_binding')
            if any(t.value=='await' for t in b) and 'async' not in method['modifiers']: raise Unknown('await_outside_async')
            local=b[1].value; sql=b[3].value[1:-1]
            # Escapes are not SQL syntax in this deliberately small literal subset.
            sqlmatch=re.fullmatch(r'SELECT\s+([A-Za-z_][A-Za-z0-9_]*(?:\s*,\s*[A-Za-z_][A-Za-z0-9_]*)*)\s+FROM\s+[A-Za-z_][A-Za-z0-9_]*\s+WHERE\s+[A-Za-z_][A-Za-z0-9_]*\s+(LIKE|=)\s+\?',sql)
            if not sqlmatch or (sql_kind=='LIKE' and sqlmatch[2]!='LIKE'): raise Unknown('sql_literal')
            projection=tuple(x.strip() for x in sqlmatch[1].split(','))
            if len({x.lower() for x in projection})!=len(projection): raise Unknown('duplicate_projection')
            for j,t in enumerate(b[:-1]):
                if t.value == 'return' and any(c in source[t.end:b[j+1].start] for c in ('\n','\r','\u2028','\u2029')):
                    raise Unknown('return_line_terminator')
            if len(b)<5 or (b[4].value!=';' and not any(c in source[b[3].end:b[4].start] for c in ('\n','\r'))):
                raise Unknown('missing_const_statement_boundary')
            rest=compact(b[4:]); rest=rest[1:] if rest.startswith(';') else rest
            rx=r'return (?:await )?this\.('+IDENT+r')\('+re.escape(local)+r',\['+re.escape(param[1])+r'\]\);?'
            call=re.fullmatch(rx,rest)
            if not call: raise Unknown('sql_forward')
            matches.append(dict(**sql_result(source,owner,method,call[1]),projection_identifiers=projection,owner=owner['name'],method=method['name'],declaration=method,method_span=method['span'],parameter=param[1],sql=sql,sql_span=span(source,b[3:4]),local=local,callee=call[1],body_span=method['body_span']))
        return dict(status='known',matches=matches)
    except (Unknown,IndexError,TypeError,KeyError,AttributeError) as e:
        return dict(status='unknown',reason=str(e),matches=[])


def classify_ui_owner(source,owner,M,V):
    try:
        authenticated(source,owner)
        if not re.fullmatch(IDENT,M) or not re.fullmatch(IDENT,V): raise Unknown('request')
        deco={d['name'] for d in owner['decorators']}
        if not deco.intersection({'Component','ComponentV2'}): return dict(status='known',chains=[])
        fields={f['name']:f for f in owner['fields']}
        if V not in fields: return dict(status='known',chains=[])
        state=fields[V]; required='Local' if 'ComponentV2' in deco else 'State'
        if [d['name'] for d in state['decorators']] != [required]: raise Unknown('state')
        submissions=[]
        for m in owner['methods']:
            b=compact(m['_body'])
            match=re.fullmatch(r'this\.'+re.escape(V)+r'=await this\.('+IDENT+r')\.'+re.escape(M)+r'\(this\.('+IDENT+r')\);?',b)
            if match: submissions.append((m,match[1],match[2]))
        if len(submissions)!=1: raise Unknown('submit_count')
        submit,receiver,input_name=submissions[0]
        if submit['parameters'] or 'async' not in submit['modifiers']: raise Unknown('submit_signature')
        f=fields.get(receiver); inp=fields.get(input_name)
        if not f or not inp or [d['name'] for d in inp['decorators']] != [required]: raise Unknown('receiver_or_input')
        if f['initializer']!='new '+f['type']+'()' or f['decorators']: raise Unknown('receiver_initialization')
        imports=[x for x in owner._imports if x['local']==f['type']]
        if len(imports)!=1: raise Unknown('receiver_import')
        # Receiver may only be used as a direct call receiver. This also rejects
        # aliases and writes anywhere in the owner, including nested callbacks.
        bodies=[m['_body'] for m in owner['methods']] + [x['_initializer'] for x in owner['fields']]
        for b in bodies:
            for i,t in enumerate(b):
                if t.value == 'this' and (i+1 == len(b) or b[i+1].value != '.'):
                    raise Unknown('computed_receiver_or_this_alias')
            for i in range(len(b)-2):
                if [t.value for t in b[i:i+3]]==['this','.',receiver]:
                    if i+5>=len(b) or b[i+3].value!='.' or b[i+4].kind!='ident' or b[i+5].value!='(':
                        raise Unknown('receiver_write_or_alias')
        builds=[x for x in owner['methods'] if x['name']=='build']
        if len(builds)!=1: raise Unknown('build')
        build=builds[0]; body=compact(build['_body'])
        cb=r'(?:\(\)=>this\.'+re.escape(submit['name'])+r'\(\)|\(\)=>\{this\.'+re.escape(submit['name'])+r'\(\);?\})'
        search=r'Search\(\{value:\$\$this\.'+re.escape(input_name)+r'\}\)\.onSubmit\('+cb+r'\);?'
        element,element_import=ui_element(owner,state)
        accepted=None
        for nested in (False,True):
            item,render=render_pattern(element,nested)
            loop=r'ForEach\(this\.'+re.escape(V)+r',\('+item+':'+re.escape(element)+r'\)=>\{'+render+r'\}\);?'
            if nested: loop=r'List\(\)\{'+loop+r'\}'
            accepted=re.fullmatch(r'Column\(\)\{'+search+loop+r'\}',body)
            if accepted:break
        if not accepted: raise Unknown('build_shape')
        item_identifier=accepted['item']
        render_field=None if element=='string' else accepted['field']
        bt=build['_body']; st=submit['_body']; bp=pairs(bt)
        search_index=next(i for i,t in enumerate(bt) if t.value=='Search')
        callback_index=next(i for i,t in enumerate(bt) if t.value=='onSubmit')
        render_index=next(i for i,t in enumerate(bt) if t.value=='ForEach')
        search_span=span(source,bt[search_index:bp[callback_index+1]+1])
        callback_span=span(source,bt[callback_index+2:bp[callback_index+1]])
        render_span=span(source,bt[render_index:bp[render_index+1]+1])
        member_span=None
        if render_field is not None:
            text_index=next(i for i,t in enumerate(bt) if t.value=='Text')
            member_span=span(source,bt[text_index+2:bp[text_index+1]])
        chain=dict(element_type=element,element_import=element_import,item_identifier=item_identifier,render_field=render_field,member_expression_span=member_span,search_span=search_span,callback_span=callback_span,render_span=render_span,owner=owner['name'],method=M,sql_method=M,receiver_import=imports[0],submit_declaration=submit,build_declaration=build,state=V,submit=submit['name'],submit_span=submit['span'],build_span=build['span'],receiver=receiver,receiver_type=f['type'],receiver_span=f['span'],import_binding=imports[0],state_span=state['span'],input=input_name,input_span=inp['span'],assignment_span=span(source,st),build_body_span=span(source,bt))
        return dict(status='known',chains=[chain])
    except (Unknown,IndexError,TypeError,KeyError,AttributeError) as e:
        return dict(status='unknown',reason=str(e),chains=[])
