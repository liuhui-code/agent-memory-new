"""Finite object-result syntax additions; no file or database reads."""
import re
from .sql_slot_source_inventory import Unknown, lex, pairs, span, legal_binding

IDENT=r'[A-Za-z_$][A-Za-z0-9_$]*'


def named_import(owner,name):
    found=[x for x in owner._imports if x['local']==name]
    if len(found)!=1 or found[0]['imported']!=name:
        raise Unknown('object_import_not_plain_named')
    return found[0]


def sql_result(source,owner,method,callee):
    if method['return_type']=='':
        # Legacy evidence certifies SQL binding only; never infer entity type.
        return dict(result_type=None,result_import=None,helper_declaration=None,return_type_span=None)
    match=re.fullmatch(r'Promise<('+IDENT+r')\[\]>',method['return_type'])
    if not match:
        # Legacy SQL binding does not certify arbitrary result annotations.
        # Preserve binding evidence without interpreting this spelling as a type.
        return dict(result_type=None,result_import=None,helper_declaration=None,return_type_span=None)
    result=match[1]
    if result=='string':
        return dict(result_type='string',result_import=None,helper_declaration=None,return_type_span=None)
    if not legal_binding(result): raise Unknown('result_type')
    binding=named_import(owner,result)
    helpers=[m for m in owner['methods'] if m['name']==callee]
    if len(helpers)!=1 or helpers[0]['return_type']!=method['return_type']:
        raise Unknown('helper_result_annotation')
    tokens=[t for t in lex(source) if method['span']['start_offset']<=t.start and t.end<=method['span']['end_offset']]
    start=next(i for i,t in enumerate(tokens) if t.value=='(')
    end=pairs(tokens)[start]
    if tokens[end+1].value!=':': raise Unknown('return_type_span')
    body=next(i for i in range(end+2,len(tokens)) if tokens[i].value=='{')
    return dict(result_type=result,result_import=binding,helper_declaration=helpers[0],return_type_span=span(source,tokens[end+2:body]))


def ui_element(owner,state):
    match=re.fullmatch('('+IDENT+r')\[\]',state['type'])
    if not match: raise Unknown('state_array_annotation')
    element=match[1]
    if element=='string':return element,None
    if not legal_binding(element):raise Unknown('element_type')
    return element,named_import(owner,element)


def render_pattern(element,nested=False):
    item=r'(?P<item>'+IDENT+r')'
    render=r'Text\((?P=item)'+('' if element=='string' else r'\.(?P<field>'+IDENT+r')')+r'\);?'
    if nested:render=r'ListItem\(\)\{'+render+r'\}'
    return item,render
