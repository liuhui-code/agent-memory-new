import unittest
from tools.agent_memory_runtime.ui_vertical_inventory import inventory_vertical_file, lex
from tools.agent_memory_runtime.ui_vertical_list_source import parse_vertical_list_file


def file_with(template,body=None):
    return 'class QueueSummary { render(){ '+(body if body is not None else 'return '+template+';')+' } }'

def inventory(source):return inventory_vertical_file(source,allow_templates=True)

class VerticalTemplateTests(unittest.TestCase):
    def test_legacy_and_exact_bool_gate(self):
        source=file_with('`Queue ${this.count}`')
        self.assertIsNone(inventory_vertical_file(source));self.assertIsNotNone(inventory(source))
        for value in (1,0,None,'true',[],{}):self.assertIsNone(inventory_vertical_file(source,allow_templates=value))
    def test_accepted_atoms_and_parentheses(self):
        for expression in ('item','item.caption','this.count','this.records.length','"class } text"',"'import {'",'0','23.5','true','false','null','((this.count))','( /* class { } */ this . count )'):
            with self.subTest(expression=expression):self.assertIsNotNone(inventory(file_with('`Value ${'+expression+'}`')))
    def test_openers(self):
        for body in ('display(`Value ${this.count}`);','display(1, `Value ${this.count}`);','const text = `Value ${this.count}`;','return `Value ${this.count}`;'):
            self.assertIsNotNone(inventory(file_with('',body)))
        for body in ('return\n`value`;','return /*\n*/ `value`;','tag`value`;','tag /* comment */ `value`;','x, `value`;','object.tag`value`;','(tag)`value`;','display()`value`;'):
            with self.subTest(body=body):self.assertIsNone(inventory(file_with('',body)))
        self.assertIsNone(inventory('`value`'))
    def test_suffixes(self):
        for suffix in ('.length','[0]','()','`next`',' + 1',' as Name'):
            self.assertIsNone(inventory(file_with('', 'return `text`'+suffix+';')))
        for body in ('return `text`;', 'display(`text`, 1);','const a=[(`text`)];','return `text` }'):
            if body.endswith('}'):continue
            self.assertIsNotNone(inventory(file_with('',body)))
    def test_raw_escape_parity_and_literal_keywords(self):
        for raw in (r'class Ghost {} /* raw */ / text',r'\${notCode}',r'\\${this.count}',r'\`quoted\`',r'\$ \n \r \t \b \f \v \0 \x41 \u0041','first\nsecond','first\r\nsecond'):
            with self.subTest(raw=raw):self.assertIsNotNone(inventory(file_with('`'+raw+'`')))
        tokens,_=lex(file_with(r'`\${literal} \\${this.count}`'),allow_templates=True)
        self.assertEqual(sum(t.kind=='interpolation_open'for t in tokens),1)
        self.assertEqual([t.value for t in tokens if t.kind=='name' and t.value=='this'],['this'])
    def test_malformed_and_unknowns(self):
        for expr in ('','this','call()','item[0]','item?.name','x=1','x+1','x?y:z','()=>1','{}','[]','`nested`','/x/','a/b','class Hidden {}','function(){}','import("m")','require','type','this.class','this.count extra'):
            with self.subTest(expr=expr):self.assertIsNone(inventory(file_with('`Value ${'+expr+'}`')))
        for template in ('`unclosed', '`x ${this.count`', '`x ${"bad}`', '`x ${/* open}`',r'`\q`',r'`\01`',r'`\u{41}`',r'`\xG0`','`\\\n`','`x ${(this.count}`'):
            with self.subTest(template=template):self.assertIsNone(inventory(file_with(template)))
    def test_expression_comments_and_exact_offsets(self):
        source=file_with('`first\n${ /* } class */ (this.count) } end`')
        tokens,pairs=lex(source,allow_templates=True)
        expr=next(t for t in tokens if t.kind=='name'and t.value=='this')
        self.assertEqual(source[expr.start:expr.end],'this');self.assertEqual(expr.line,2)
        for t in tokens:
            if t.kind in {'template_open','template_close','interpolation_open','interpolation_close','template_raw'}:
                self.assertEqual(source[t.start:t.end],t.value)
        self.assertTrue(pairs)
    def test_inventory_late_name_and_independent_unknown(self):
        source=file_with('`class NotReal ${this.count}`')+' class CedarLate {}'
        self.assertEqual([d.name for d in inventory(source).declarations],['QueueSummary','CedarLate'])
        self.assertIsNone(inventory(source+' class Extra { x=/regex/ }'))
    def test_positive_parser_never_inherits_permission(self):
        source="@Component struct CedarPane { @State rows:string[]=[]; build(){ List(){ ForEach(this.rows,(row:string)=>{ListItem(){Text(`Queued ${row}`)}}) }.listDirection(Axis.Vertical) } }"
        self.assertIsNotNone(inventory(source));self.assertIsNone(parse_vertical_list_file(source,{'CedarPane'}))
    def test_interpolation_and_depth_limits(self):
        self.assertIsNotNone(inventory(file_with('`'+'${this.count}'*256+'`')))
        self.assertIsNone(inventory(file_with('`'+'${this.count}'*257+'`')))
        self.assertIsNone(inventory(file_with('`'+'${this.count}'*128+'`',body='return `'+'${this.count}'*128+'`; display(`'+'${this.count}'*129+'`);')))
        self.assertIsNotNone(inventory(file_with('`${'+'('*252+'x'+')'*252+'}`')))
        self.assertIsNone(inventory(file_with('`${'+'('*253+'x'+')'*253+'}`')))
