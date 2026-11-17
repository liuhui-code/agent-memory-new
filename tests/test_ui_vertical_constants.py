"""Literal-binding lexical units, not normal CLI or public qualification proof."""
import unittest
from tools.agent_memory_runtime.ui_vertical_inventory import inventory_vertical_file
from tools.agent_memory_runtime.ui_vertical_list_source import parse_vertical_list_file


def parse(s,**kwargs):return inventory_vertical_file(s,allow_literal_constants=True,**kwargs)

class VerticalConstantsTests(unittest.TestCase):
    def test_default_and_bool_gate(self):
        s='const Settings = {caption: "ready"}'
        self.assertIsNone(inventory_vertical_file(s));self.assertIsNone(inventory_vertical_file(s,allow_templates=True))
        self.assertIsNotNone(parse(s))
        for value in (1,0,None,'true',[],{}):self.assertIsNone(inventory_vertical_file(s,allow_literal_constants=value))
    def test_primitive_kinds_empty_trailing_comma(self):
        for body in ('','label:"hello"','count:0, ratio:2.5, enabled:true, hidden:false, missing:null,','text:"class Fake {}", marker:"null", __private:3'):
            with self.subTest(body=body):self.assertIsNotNone(parse('export const Settings = {'+body+'};'))
    def test_exact_offsets_and_object_span(self):
        source='// preface\nexport const Settings = {\n  count: 2,\n};\nclass Other {}'
        p=parse(source);d=p.declarations[0]
        self.assertEqual((d.name,d.kind,d.start_line,d.end_line),('Settings','literal_const',2,4))
        self.assertEqual(source[d.start:d.end],'const Settings = {\n  count: 2,\n}')
        self.assertEqual(source[d.body_start:d.body_end],'{\n  count: 2,\n}')
        self.assertEqual([d.name for d in p.declarations],['Settings','Other'])
    def test_keys_and_binding_unknowns(self):
        for body in ('key:1,key:2','__proto__:null','class:1','symbol:1','"key":1','[key]:1','key','...other','get key(){return 1}','key(){return 1}','key:1,,','key:1;other:2'):
            with self.subTest(body=body):self.assertIsNone(parse('const Settings={'+body+'}'))
        for name in ('List','Axis','ForEach','ListItem','Text','Column','Row','Scroll','State','Component','Entry','class'):
            self.assertIsNone(parse('const '+name+'={}'))
    def test_numeric_and_nonliteral_values(self):
        for value in ('-1','+1','1e2','0x10','NaN','Infinity','1'*33,'01','.5','1.','123n','other','other.value','call()','[]','{}','`literal`','true.value','null()','false ? 1 : 2'):
            with self.subTest(value=value):self.assertIsNone(parse('const Settings={key:'+value+'}',allow_templates=True))
    def test_declaration_forms_remain_unknown(self):
        for s in ('let Settings={}','var Settings={}','const A={},B={}','const {A}={}','const A:Shape={}','const A={} as Shape','const A={} satisfies Shape','@State const A={}','@State export const A={}','export default const A={}','const A=({})','const A={}; function f(){}','"const" A={}'):self.assertIsNone(parse(s))
    def test_termination_and_continuations(self):
        for s in ('const A={}','const A={};class B{}','const A={}\nclass B{}','const A={}\nconst B={}'):self.assertIsNotNone(parse(s))
        for suffix in ('class B{}','const B={}','.value','\n.value','\n[0]','\n()','\n+1','\nwith {}','\nassert {}','\n`tag`'):
            self.assertIsNone(parse('const A={}'+suffix,allow_templates=True))
    def test_import_to_const_optin_only(self):
        s="import Helper from 'm'\nconst Settings={}"
        self.assertIsNone(inventory_vertical_file(s));p=parse(s);self.assertIsNotNone(p)
        self.assertEqual(p.imports[0].local,'Helper');self.assertEqual(p.declarations[0].name,'Settings')
        self.assertIsNone(parse("import Helper from 'm' const Settings={}"))
    def test_duplicate_and_forward_collisions(self):
        for s in ('const A={};const A={}','class A{} const A={}','const A={};class A{}',"import A from 'm';const A={}","const A={};import A from 'm'",'interface A{} const A={}'):self.assertIsNone(parse(s))
    def test_matching_constant_not_hidden_or_positive(self):
        s='const CedarConfig={caption:"ready"}; class Other{}';p=parse(s)
        self.assertEqual(p.declarations[0].name,'CedarConfig');self.assertEqual(p.declarations[0].kind,'literal_const')
        self.assertIsNone(parse_vertical_list_file(s,{'CedarConfig'}))
    def test_caps_and_no_partial_result(self):
        self.assertIsNotNone(parse(' '.join('const A%d={};'%i for i in range(4096))))
        self.assertIsNone(parse(' '.join('const A%d={};'%i for i in range(4097))))
        self.assertIsNone(parse('const Valid={}; const Broken={key:call()}'))
