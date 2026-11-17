import dataclasses
import unittest
from tools.agent_memory_runtime.ui_vertical_inventory import inventory_vertical_file

class VerticalInventoryTests(unittest.TestCase):
    def test_opaque_decorated_async_operator_body(self):
        s="@ComponentV2\nexport struct OtherPane { @Prop count:number=0; @Builder helper(){this.count++;} async load():Promise<void>{this.count = (this.count + 2) * 3; const text='class Fake {}';} }"
        p=inventory_vertical_file(s);self.assertIsNotNone(p);self.assertEqual(p.declarations[0].name,'OtherPane')
        with self.assertRaises(dataclasses.FrozenInstanceError):p.token_count=0
    def test_three_static_imports_and_ranges(self):
        s="import Thing from './a';\nimport { One, Two as Second, } from './b'\nimport * as Namespace from './c'\nclass Owner {}"
        p=inventory_vertical_file(s);self.assertEqual([i.local for i in p.imports],['Thing','One','Second','Namespace']);self.assertEqual([i.form for i in p.imports],['default','named','named','namespace']);self.assertEqual(p.declarations[0].start_line,4)
        self.assertEqual(p.imports[2].remote,'Two');self.assertEqual(p.imports[3].module,'./c')
    def test_subject_alias_retained_for_caller(self):
        p=inventory_vertical_file("import { Other as CratePane } from 'm'; class Unrelated {}")
        self.assertEqual(p.imports[0].local,'CratePane')
    def test_import_unknown_forms(self):
        bad=["import 'm'", "import {} from 'm'", "import A, { B } from 'm'", "import type { A } from 'm'", "import { default as A } from 'm'", "import { 'x' as A } from 'm'", "import A = require('m')", "import('m')", "export { A } from 'm'", "import A from 'm' with {type:'x'}", "import A from 'm' assert {}", "import A from 'm' class X {}", "import A 'from' 'm'", "import { A 'as' B } from 'm'", "import A from 'm'\n.foo", "class X { import A from 'm'; }"]
        for s in bad:
            with self.subTest(s=s):self.assertIsNone(inventory_vertical_file(s))
    def test_duplicate_forward_and_critical_alias(self):
        for s in ("import A from 'm'; class A {}", "class A {} import A from 'm';", "class A {} interface A {}", "import { A, B as A } from 'm'", "import { Other as List } from 'm'", "import * as Axis from 'm'"):
            with self.subTest(s=s):self.assertIsNone(inventory_vertical_file(s))
    def test_all_nested_declaration_words_inspected(self):
        for word in ('class','struct','interface','function','import','export','type','enum','namespace','module','require'):
            s='class Outer { helper(){ if(true){ '+word+' Inner {} } } }'
            with self.subTest(word=word):self.assertIsNone(inventory_vertical_file(s))
        self.assertIsNone(inventory_vertical_file('class Outer { helper(){ const callback=function(){} } }'))
    def test_quoted_keyword_and_comments_inert(self):
        p=inventory_vertical_file("// class Fake {}\nclass Real { text(){ return 'struct Ghost {}'; } /* interface Nope {} */ }")
        self.assertEqual([d.name for d in p.declarations],['Real'])
        for s in ('"class" Fake {}', "export 'struct' Fake {}", 'class X { obj.class; }', 'class X { const x={class:1}; }'):
            self.assertIsNone(inventory_vertical_file(s))
    def test_unsupported_lexical_header_and_decorator(self):
        for s in ('class X { x=/a/ }','class X { x=a/b }','class X { x=`text` }',r'class X { \u0061=1 }','class X { x=0xff }','class X { x=1e3 }','class X { x="bad\\q" }','class X { /*','class X { x=(] }','class X extends Y {}','class X<T> {}','function named(){}','const x=1','@A() class X {}','@A.B class X {}','class X { @A() x=1 }'):
            with self.subTest(s=s):self.assertIsNone(inventory_vertical_file(s))
    def test_source_only_matching_and_late_declarations_preserved(self):
        p=inventory_vertical_file('class Unrelated {} @Component struct CrateHidden {} interface CrateShape {}')
        self.assertEqual([d.name for d in p.declarations],['Unrelated','CrateHidden','CrateShape'])
    def test_resource_bounds(self):
        self.assertIsNone(inventory_vertical_file(' '*(2*1024*1024+1)))
        self.assertIsNotNone(inventory_vertical_file('class X {'+'('*255+')'*255+'}'))
        self.assertIsNone(inventory_vertical_file('class X {'+'('*256+')'*256+'}'))
        self.assertIsNotNone(inventory_vertical_file(' '.join('class X%d {}'%i for i in range(4096))))
        self.assertIsNone(inventory_vertical_file(' '.join('class X%d {}'%i for i in range(4097))))
        self.assertIsNone(inventory_vertical_file('class X {'+'x;'*100001+'}'))
    def test_empty_and_bad_input(self):
        self.assertEqual(inventory_vertical_file('// comment').declarations,())
        for s in (None,b'class X {}','\ud800'):self.assertIsNone(inventory_vertical_file(s))

    def test_exact_token_limit_and_one_over(self):
        # Header/open/close contribute four tokens; body identifiers are opaque.
        exact='class X {'+'x '*199996+'}'
        inventory=inventory_vertical_file(exact)
        self.assertIsNotNone(inventory)
        self.assertEqual(inventory.token_count,200000)
        self.assertIsNone(inventory_vertical_file('class X {'+'x '*199997+'}'))

    def test_active_unicode_identifiers_and_line_separators_unknown(self):
        for source in ('class 名称 {}','class Caf\u00e9 {}','class X { caf\u00e9=1; }','class X { x\u2028y }','class X { x\u2029y }'):
            with self.subTest(source=source):
                self.assertIsNone(inventory_vertical_file(source))
