# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Unexecuted fixed resource tests; no production implementation or CLI."""
import importlib
import unittest


def candidate():
    try:
        module=importlib.import_module('tools.agent_memory_runtime.query_validation_binding_resources')
        return module.bounded_binding_parts
    except (ImportError, AttributeError) as error:
        raise NotImplementedError('bounded_binding_parts not implemented; not semantic red') from error


def cases():
    good=(('src/Panel.ts','a'*64),)
    result=[]
    def add(name, expected, metadata=None,files=(),state='',proof=''):
        result.append((name,expected,(metadata,files,state,proof)))
    add('empty-resource-parts',True)
    add('valid-long-derived',True,files=good,state='x'*20000,proof='y'*40000)
    add('same-named-raw-key-no-exemption',False,metadata={'state':'x'*16385})
    add('raw-proof-key-no-exemption',False,metadata={'proof':'x'*16385})
    add('raw-at-scalar-limit',True,metadata={'proof':'x'*16384})
    add('aggregate-at-limit',True,state='x'*1048576)
    add('aggregate-one-over',False,state='x'*1048577)
    add('split-aggregate-at-limit',True,state='x'*524288,proof='y'*524288)
    add('split-aggregate-one-over',False,state='x'*524288,proof='y'*524289)
    add('metadata-counted-at-limit',True,metadata='m',state='x'*1048575)
    add('metadata-counted-one-over',False,metadata='m',state='x'*1048576)
    cost=len('src/Panel.ts'.encode())+64
    add('files-counted-at-limit',True,files=good,state='x'*(1048576-cost))
    add('files-counted-one-over',False,files=good,state='x'*(1048577-cost))
    add('multibyte-chunk-crossing',True,state='x'*16383+'😀'+'y')
    add('multibyte-total-at-limit',True,state='😀'*262144)
    add('multibyte-total-one-over',False,state='😀'*262144+'x')
    add('surrogate-state',False,state='\ud800')
    add('surrogate-proof',False,proof='\udfff')
    add('files-list-not-tuple',False,files=list(good))
    add('pair-list-not-tuple',False,files=(list(good[0]),))
    add('files12',True,files=tuple(('p%d.ts'%n,'a'*64) for n in range(12)))
    add('files13',False,files=tuple(('p%d.ts'%n,'a'*64) for n in range(13)))
    add('duplicate-path',False,files=good+good)
    for name,path in [('absolute','/a.ts'),('parent','../a.ts'),('dot','a/./b.ts'),('empty-segment','a//b.ts'),('backslash','a\\b.ts'),('empty',''),('hash','a#b.ts'),('nul','a\0b.ts')]:
        add('path-'+name,False,files=((path,'a'*64),))
    for name,digest in [('short','a'*63),('long','a'*65),('nonhex','g'*64),('uppercase','A'*64),('number',64)]:
        add('digest-'+name,False,files=(('p.ts',digest),))
    add('syntactically-valid-false-digest',True,files=(('p.ts','0'*64),))
    cycle=[];cycle.append(cycle);add('metadata-cycle',False,metadata=cycle)
    add('huge-integer',False,metadata=1<<64)
    add('int64',True,metadata=1<<63)
    add('short-forged-derived-resource-only',True,state='forged',proof='forged')
    class Text(str):pass
    class Tuple(tuple):pass
    add('custom-state',False,state=Text('x'))
    add('custom-proof',False,proof=Text('x'))
    add('custom-files',False,files=Tuple(good))
    add('custom-pair',False,files=(Tuple(good[0]),))
    add('custom-path',False,files=((Text('p.ts'),'a'*64),))
    add('raw-files-tuple-no-exemption',False,metadata={'files':good})
    # R root1 + metadata-list1 + leavesN + files-list1 + two chunk-lists2.
    add('nodes-at-limit',True,metadata=[None]*(16384-5))
    add('nodes-one-over',False,metadata=[None]*(16384-4))
    for depth,expected in [(11,True),(12,False)]:
        value=None
        for _ in range(depth):value=[value]
        add('combined-depth-'+str(depth),expected,metadata=value)
    return result


class BindingResourceContract(unittest.TestCase):
    def test_fixed_cases(self):
        check=candidate()
        for name,expected,args in cases():
            with self.subTest(name=name):
                actual=check(*args)
                self.assertIs(type(actual),bool)
                self.assertIs(actual,expected)


if __name__=='__main__':
    raise SystemExit('DRAFT: explicit review/freeze required before invocation')
