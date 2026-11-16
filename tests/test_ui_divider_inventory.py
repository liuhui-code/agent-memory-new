"""Declaration-only punctuation coverage; no query/oracle changes or producer authority."""
import tempfile
import unittest
from pathlib import Path
from tools.agent_memory_runtime.ui_divider_source import tokenize, Unknown, parse_ui_divider_file
from tools.agent_memory_runtime.query_ui_divider_method_scope import source_component_names, method_rooted_frames
from tools.agent_memory_runtime.query_ui_divider_negative import exact_negative_declaration


COMPATIBLE="""@Component
export struct StatusPane {
 @State failureText: string = ''
 @State ready: boolean = false
 clearFailure(): void {
  this.failureText = ''
  this.ready = true
 }
 build() {
  Text(this.failureText)
 }
}
"""

def state_source(generic=False, negate=False):
    source=COMPATIBLE
    if generic:source=source.replace('clearFailure(): void', 'async clearFailure(): Promise<void>')
    if negate:source=source.replace('this.ready = true', 'this.ready = !this.ready')
    return source


class DividerInventoryLexicalTests(unittest.TestCase):
    def test_only_explicit_true_enables_new_inventory_punctuation(self):
        for generic,negate in ((True,False),(False,True),(True,True)):
            source=state_source(generic,negate)
            self.assertEqual(source_component_names(source),{'StatusPane'})
            tokenize(source,declaration_inventory=True)
            for flag in (False,None,1,'true'):
                with self.subTest(generic=generic,negate=negate,flag=flag):
                    with self.assertRaises(Unknown):tokenize(source,declaration_inventory=flag)
            with self.assertRaises(Unknown):tokenize(source)

    def test_compatible_sequence_and_pairs_identical(self):
        ordinary=tokenize(COMPATIBLE)
        self.assertEqual(ordinary,tokenize(COMPATIBLE,declaration_inventory=False))
        self.assertEqual(ordinary,tokenize(COMPATIBLE,declaration_inventory=True))
        self.assertEqual(source_component_names(COMPATIBLE),{'StatusPane'})

    def test_default_positive_parser_never_inherits_inventory_permission(self):
        baseline="@Component\nexport struct GlyphCard {\n build() {\n  List() { ListItem() { Text('sample') } }.divider({ strokeWidth: 2 })\n }\n}\n"
        self.assertIsNotNone(parse_ui_divider_file(baseline,['GlyphCard']))
        for line in (' pending: Promise<void>\n',' active: boolean = !false\n'):
            source=baseline.replace(' build()',line+' build()')
            self.assertEqual(source_component_names(source),{'GlyphCard'})
            self.assertIsNone(parse_ui_divider_file(source,['GlyphCard']))

    def test_negative_parser_remains_default(self):
        source="export class Excluded {\n ready: boolean = false\n}\n"
        row=dict(symbol='Excluded',symbol_type='class',start_line=1,end_line=3)
        self.assertTrue(exact_negative_declaration(source,row))
        for replacement in (' ready: Promise<void>\n',' ready: boolean = !false\n'):
            changed=source.replace(' ready: boolean = false\n',replacement)
            self.assertFalse(exact_negative_declaration(changed,row))

    def test_string_and_comment_structs_never_names(self):
        source=state_source(True,True).replace(" @State failureText: string = ''", " @State failureText: string = 'struct GlyphPretend { build() {} }'\n // struct GlyphLine {}\n /* @Component struct GlyphBlock {} */")
        self.assertEqual(source_component_names(source),{'StatusPane'})
        source+='@Component\nexport struct ActualPanel {\n build() { Text(\'sample\') }\n}\n'
        self.assertEqual(source_component_names(source),{'StatusPane','ActualPanel'})

    def test_unknown_lexical_shapes_still_fail_closed(self):
        extras=[' pattern: RegExp = /glyph{1,2}/\n',' label: string = `glyph ${this.ready}`\n'," label: string = '\\q'\n", " label: string = 'unfinished\n",' value: number = §\n',' value: number = 1 + 2\n',' value: number = 2 - 1\n',' value: number = 2 * 1\n',' value: number = 2 / 1\n',' value: number = 2 % 1\n',' value: boolean = true && false\n',' value: boolean = true || false\n',' value: string = this.ready ? \'yes\' : \'no\'\n']
        for extra in extras:
            source=COMPATIBLE.replace(' clearFailure()',extra+' clearFailure()')
            with self.subTest(extra=extra):
                with self.assertRaises(Unknown):tokenize(source,declaration_inventory=True)
                self.assertIsNone(source_component_names(source))
        for source in (COMPATIBLE[:-2],COMPATIBLE.replace('Text(this.failureText)','Text(this.failureText]'),'/* unclosed\n'+COMPATIBLE):
            with self.subTest(source=source):
                with self.assertRaises(Unknown):tokenize(source,declaration_inventory=True)
                self.assertIsNone(source_component_names(source))

    def test_hidden_matching_declaration_requires_original_pool_build(self):
        # Normal producer; manipulated pool is a labeled UNIT control, not public recall.
        from tests.archive_create_write_test_support import cli
        from tools.agent_memory_runtime.storage import resolve_project, connect
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'source';root.mkdir()
            source=state_source(True,True)+"@Component\nexport struct GlyphSilent {\n build() {\n  List() { ListItem() { Text('sample') } }.divider({ strokeWidth: 2 })\n }\n}\n"
            (root/'StatusPane.ets').write_text(source)
            project=resolve_project(str(root),str(Path(temporary)/'memory'))
            cli(project,'init');cli(project,'learn-path','--path','.','--json')
            with connect(project) as db:
                symbols=[dict(r,kind='symbol')for r in db.execute('SELECT * FROM code_symbols WHERE project_id=?',(project.project_id,))]
            other=next(r for r in symbols if r['symbol']=='failureText' and r['symbol_type']=='state')
            build=next(r for r in symbols if r['symbol']=='build' and r['owner_name']=='GlyphSilent')
            self.assertEqual(source_component_names(source),{'StatusPane','GlyphSilent'})
            self.assertIsNone(method_rooted_frames(project,[other],('glyph',)))
            complete=method_rooted_frames(project,[other,build],('glyph',))
            self.assertIsNotNone(complete)
            self.assertEqual([frame['owner']['symbol']for frame in complete[0]],['GlyphSilent'])
