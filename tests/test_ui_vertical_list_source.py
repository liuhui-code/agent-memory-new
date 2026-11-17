import unittest
from tools.agent_memory_runtime.ui_vertical_list_source import parse_vertical_list_file


def source(owner='BoxPane',typ='string',param='item',field='rows',member=None):
    text=param+'.'+member if member else param
    return f'''@Component
export struct {owner} {{
  @State {field}: {typ}[] = []
  build() {{
    Column() {{
      List() {{
        ForEach(this.{field}, ({param}: {typ}) => {{
          ListItem() {{
            Text({text})
          }}
        }})
      }}.listDirection(Axis.Vertical).height('100%')
    }}
  }}
}}
'''

class VerticalSourceTests(unittest.TestCase):
    def test_primitive_nominal_and_arbitrary_names(self):
        for typ,param,field,member in [('string','item','rows',None),('number','n','values',None),('boolean','flag','flags',None),('OpaqueRecord','record','entries','caption'),('Shipment','shipment','shipments','label')]:
            s=source(typ=typ,param=param,field=field,member=member)
            with self.subTest(typ=typ):
                p=parse_vertical_list_file(s,{'BoxPane'})
                self.assertIsNotNone(p);self.assertEqual(p['BoxPane']['build_start'],4);self.assertEqual(p['BoxPane']['build_end'],14)
                self.assertTrue(p['BoxPane']['positive']);self.assertEqual(p['BoxPane']['sites'][0]['bindings'][0]['field'],field)
    def test_complete_inventory_and_two_positive(self):
        s=source()+source('OtherBoxPane')+"class CodeMaker { makeCode(): string { return 'code' } }"
        p=parse_vertical_list_file(s,{'BoxPane','OtherBoxPane'})
        self.assertEqual(set(p),{'BoxPane','OtherBoxPane'});self.assertEqual(set(p.declared_names),{'BoxPane','OtherBoxPane','CodeMaker'})
        self.assertIsNone(parse_vertical_list_file(s,{'Missing'}))
    def test_wrong_axis_default_and_competing_scroll(self):
        base=source()
        for s in (base.replace('Axis.Vertical','Axis.Horizontal'),base.replace('.listDirection(Axis.Vertical)',''),base.replace('.height', '.listDirection(Axis.Vertical).height'),base.replace('List() {','Scroll() {')):
            with self.subTest(s=s):self.assertIsNone(parse_vertical_list_file(s,{'BoxPane'}))
    def test_crossnode_sibling_is_not_composed(self):
        s=source().replace("}.listDirection(Axis.Vertical).height('100%')", "}.height('100%')\n      List() {}.listDirection(Axis.Vertical)")
        self.assertIsNone(parse_vertical_list_file(s,{'BoxPane'}))
    def test_binding_mismatch_and_unbound_text(self):
        s=source(typ='RowValue',member='caption')
        for bad in (s.replace('item: RowValue','item: OtherValue'),s.replace('this.rows','this.unknown'),s.replace('Text(item.caption)','Text(other.caption)'),s.replace('Text(item.caption)','Text(this.rows)'),s.replace('(item: RowValue)','(rows: RowValue)')):
            with self.subTest(bad=bad):self.assertIsNone(parse_vertical_list_file(bad,{'BoxPane'}))
    def test_other_collection_same_nominal_is_positive(self):
        s=source(typ='RowValue',member='caption').replace('  build()', '  @State backup: RowValue[] = []\n  build()').replace('ForEach(this.rows','ForEach(this.backup')
        self.assertIsNotNone(parse_vertical_list_file(s,{'BoxPane'}))
    def test_shadow_duplicate_and_lexical_unknown(self):
        s=source()
        for bad in (s+'class Axis {}',s.replace('rows:', 'List:'),s+s,s.replace('Text(item)','Text(item); eval()'),s+' const x = /regex/',s+' const x = `template`',s[:-2]):
            with self.subTest(bad=bad):self.assertIsNone(parse_vertical_list_file(bad,{'BoxPane'}))
    def test_string_comment_fake_inventory_ignored(self):
        s=source()+"\n// struct Ghost {}\nclass Maker { text(): string { return 'struct Fake {}' } }"
        p=parse_vertical_list_file(s,{'BoxPane'});self.assertEqual(set(p.declared_names),{'BoxPane','Maker'})
    def test_scalar_and_optional_state_height(self):
        s=source().replace('@State rows','rows').replace('  build()',"  title: string = 'name'\n  count: number = 0\n  enabled: boolean = true\n  build()").replace(".height('100%')",'')
        self.assertIsNotNone(parse_vertical_list_file(s,{'BoxPane'}))
    def test_unknown_member_and_invalid_statement_boundary(self):
        for bad in (source().replace('  build()', '  unknown: Other = make()\n  build()'),source().replace('[] = []','[] = [] more: string = \'x\''),source().replace('Text(item)','Text(item)Text(item)')):
            self.assertIsNone(parse_vertical_list_file(bad,{'BoxPane'}))
    def test_same_file_scroll_ambiguity_and_outside_subject_preserved(self):
        scroll=source('OtherPane').replace('List() {','Scroll() {').replace('.listDirection(Axis.Vertical)','')
        combined=source()+scroll
        self.assertIsNotNone(parse_vertical_list_file(combined,{'BoxPane'}))
        self.assertIsNone(parse_vertical_list_file(combined,{'BoxPane','OtherPane'}))
        bad=source().replace('ListItem() {','Column() {')
        self.assertIsNone(parse_vertical_list_file(bad,{'BoxPane'}))

    def test_string_token_is_not_type_name(self):
        for s in (source().replace(': string', ": 'string'"),source().replace('rows: string', "rows: 'string'"),source().replace('item: string', "item: 'string'")):
            with self.subTest(s=s):self.assertIsNone(parse_vertical_list_file(s,{'BoxPane'}))

    def test_unbound_literal_text_cannot_join_wanted_view(self):
        s=source().replace('Text(item)', "Text(item); Text('extra')")
        self.assertIsNone(parse_vertical_list_file(s,{'BoxPane'}))
        self.assertIsNotNone(parse_vertical_list_file(source(),{'BoxPane'}))

    def test_callback_shadows_owner_or_later_declaration(self):
        for s in (source(param='BoxPane'),source(param='Helper')+"class Helper { text(): string { return 'ok' } }"):
            with self.subTest(s=s):self.assertIsNone(parse_vertical_list_file(s,{'BoxPane'}))

    def test_scroll_any_depth_in_wanted_list_rejects(self):
        base=source()
        nested_list=base.replace('      List() {','      List() {\n        Scroll() {').replace("      }.listDirection", "        }\n      }.listDirection")
        nested_callback=base.replace('          ListItem() {','          Scroll() {\n          ListItem() {').replace('        })','          }\n        })')
        nested_item=base.replace('            Text(item)','            Scroll() { Text(item) }')
        for bad in (nested_list,nested_callback,nested_item):
            with self.subTest(bad=bad):
                self.assertIsNone(parse_vertical_list_file(bad,{'BoxPane'}))
                self.assertIsNotNone(parse_vertical_list_file(bad,set()))
        self.assertIsNotNone(parse_vertical_list_file(base,{'BoxPane'}))

    def test_quoted_declaration_keywords_are_not_declarations(self):
        for quote in ("'",'"'):
            for kind in ('struct','class','interface'):
                body=source().replace('struct',quote+kind+quote)
                with self.subTest(kind=kind,quote=quote):
                    self.assertIsNone(parse_vertical_list_file(body,{'BoxPane'}))
                    self.assertIsNone(parse_vertical_list_file(body,set()))

    def test_callback_field_shadow_is_owner_local_and_order_independent(self):
        before=source().replace('  build()', "  item: string = ''\n  build()")
        after=source().replace('  }\n}\n', "  }\n  item: string = ''\n}\n")
        for bad in (before,after):
            with self.subTest(bad=bad):self.assertIsNone(parse_vertical_list_file(bad,{'BoxPane'}))
        other=source('OtherPane',param='other').replace('  build()', "  item: string = ''\n  build()")
        self.assertIsNotNone(parse_vertical_list_file(source()+other,{'BoxPane','OtherPane'}))

    def test_empty_scope_and_invalid_inputs(self):
        self.assertEqual(parse_vertical_list_file("class Helper { text(): string { return 'ok' } }",set()),{})
        for s,n in [(None,set()),(source(),'BoxPane'),(source(),{'List'}),(' '* (2*1024*1024+1),set())]:self.assertIsNone(parse_vertical_list_file(s,n))


# Exact frozen independent source bytes only, no outputs or evaluation metadata.
FROZEN_SOURCES = {'crate-single': {'CodeMaker.ts': "export class CodeMaker {\n  makeCode(): string {\n    return 'ledger-code'\n  }\n}\n", 'ArticleScrollPane.ets': "@Component\nexport struct ArticleScrollPane {\n  @State rows: string[] = []\n  build() {\n    Scroll() {\n      Column() {\n        ForEach(this.rows, (row: string) => {\n          Text(row)\n        })\n      }\n    }.height('100%')\n  }\n}\n", 'CrateLedgerPane.ets': "@Component\nexport struct CrateLedgerPane {\n  @State rows: string[] = []\n  build() {\n    Column() {\n      List() {\n        ForEach(this.rows, (row: string) => {\n          ListItem() {\n            Text(row)\n          }\n        })\n      }.listDirection(Axis.Vertical).height('100%')\n    }\n  }\n}\n"}, 'parcel-single': {'CodeMaker.ts': "export class CodeMaker {\n  makeCode(): string {\n    return 'ledger-code'\n  }\n}\n", 'ArticleScrollPane.ets': "@Component\nexport struct ArticleScrollPane {\n  @State rows: string[] = []\n  build() {\n    Scroll() {\n      Column() {\n        ForEach(this.rows, (row: string) => {\n          Text(row)\n        })\n      }\n    }.height('100%')\n  }\n}\n", 'ParcelLedgerPane.ets': "@Component\nexport struct ParcelLedgerPane {\n  @State rows: string[] = []\n  build() {\n    Column() {\n      List() {\n        ForEach(this.rows, (row: string) => {\n          ListItem() {\n            Text(row)\n          }\n        })\n      }.listDirection(Axis.Vertical).height('100%')\n    }\n  }\n}\n"}, 'crate-two': {'CodeMaker.ts': "export class CodeMaker {\n  makeCode(): string {\n    return 'ledger-code'\n  }\n}\n", 'ArticleScrollPane.ets': "@Component\nexport struct ArticleScrollPane {\n  @State rows: string[] = []\n  build() {\n    Scroll() {\n      Column() {\n        ForEach(this.rows, (row: string) => {\n          Text(row)\n        })\n      }\n    }.height('100%')\n  }\n}\n", 'CrateLedgerPane.ets': "@Component\nexport struct CrateLedgerPane {\n  @State rows: string[] = []\n  build() {\n    Column() {\n      List() {\n        ForEach(this.rows, (row: string) => {\n          ListItem() {\n            Text(row)\n          }\n        })\n      }.listDirection(Axis.Vertical).height('100%')\n    }\n  }\n}\n", 'CrateArchivePane.ets': "@Component\nexport struct CrateArchivePane {\n  @State rows: string[] = []\n  build() {\n    Column() {\n      List() {\n        ForEach(this.rows, (row: string) => {\n          ListItem() {\n            Text(row)\n          }\n        })\n      }.listDirection(Axis.Vertical).height('100%')\n    }\n  }\n}\n"}, 'crate-with-scroll': {'CodeMaker.ts': "export class CodeMaker {\n  makeCode(): string {\n    return 'ledger-code'\n  }\n}\n", 'ArticleScrollPane.ets': "@Component\nexport struct ArticleScrollPane {\n  @State rows: string[] = []\n  build() {\n    Scroll() {\n      Column() {\n        ForEach(this.rows, (row: string) => {\n          Text(row)\n        })\n      }\n    }.height('100%')\n  }\n}\n", 'CrateLedgerPane.ets': "@Component\nexport struct CrateLedgerPane {\n  @State rows: string[] = []\n  build() {\n    Column() {\n      List() {\n        ForEach(this.rows, (row: string) => {\n          ListItem() {\n            Text(row)\n          }\n        })\n      }.listDirection(Axis.Vertical).height('100%')\n    }\n  }\n}\n", 'CrateAlternatePane.ets': "@Component\nexport struct CrateAlternatePane {\n  @State rows: string[] = []\n  build() {\n    Scroll() {\n      Column() {\n        ForEach(this.rows, (row: string) => {\n          Text(row)\n        })\n      }\n    }.height('100%')\n  }\n}\n"}, 'crate-with-column': {'CodeMaker.ts': "export class CodeMaker {\n  makeCode(): string {\n    return 'ledger-code'\n  }\n}\n", 'ArticleScrollPane.ets': "@Component\nexport struct ArticleScrollPane {\n  @State rows: string[] = []\n  build() {\n    Scroll() {\n      Column() {\n        ForEach(this.rows, (row: string) => {\n          Text(row)\n        })\n      }\n    }.height('100%')\n  }\n}\n", 'CrateLedgerPane.ets': "@Component\nexport struct CrateLedgerPane {\n  @State rows: string[] = []\n  build() {\n    Column() {\n      List() {\n        ForEach(this.rows, (row: string) => {\n          ListItem() {\n            Text(row)\n          }\n        })\n      }.listDirection(Axis.Vertical).height('100%')\n    }\n  }\n}\n", 'CrateAlternatePane.ets': "@Component\nexport struct CrateAlternatePane {\n  @State rows: string[] = []\n  build() {\n    Column() {\n      ForEach(this.rows, (row: string) => {\n        Text(row)\n      })\n    }.height('100%')\n  }\n}\n"}, 'crate-with-default': {'CodeMaker.ts': "export class CodeMaker {\n  makeCode(): string {\n    return 'ledger-code'\n  }\n}\n", 'ArticleScrollPane.ets': "@Component\nexport struct ArticleScrollPane {\n  @State rows: string[] = []\n  build() {\n    Scroll() {\n      Column() {\n        ForEach(this.rows, (row: string) => {\n          Text(row)\n        })\n      }\n    }.height('100%')\n  }\n}\n", 'CrateLedgerPane.ets': "@Component\nexport struct CrateLedgerPane {\n  @State rows: string[] = []\n  build() {\n    Column() {\n      List() {\n        ForEach(this.rows, (row: string) => {\n          ListItem() {\n            Text(row)\n          }\n        })\n      }.listDirection(Axis.Vertical).height('100%')\n    }\n  }\n}\n", 'CrateAlternatePane.ets': "@Component\nexport struct CrateAlternatePane {\n  @State rows: string[] = []\n  build() {\n    Column() {\n      List() {\n        ForEach(this.rows, (row: string) => {\n          ListItem() {\n            Text(row)\n          }\n        })\n      }.height('100%')\n    }\n  }\n}\n"}, 'crate-with-horizontal': {'CodeMaker.ts': "export class CodeMaker {\n  makeCode(): string {\n    return 'ledger-code'\n  }\n}\n", 'ArticleScrollPane.ets': "@Component\nexport struct ArticleScrollPane {\n  @State rows: string[] = []\n  build() {\n    Scroll() {\n      Column() {\n        ForEach(this.rows, (row: string) => {\n          Text(row)\n        })\n      }\n    }.height('100%')\n  }\n}\n", 'CrateLedgerPane.ets': "@Component\nexport struct CrateLedgerPane {\n  @State rows: string[] = []\n  build() {\n    Column() {\n      List() {\n        ForEach(this.rows, (row: string) => {\n          ListItem() {\n            Text(row)\n          }\n        })\n      }.listDirection(Axis.Vertical).height('100%')\n    }\n  }\n}\n", 'CrateAlternatePane.ets': "@Component\nexport struct CrateAlternatePane {\n  @State rows: string[] = []\n  build() {\n    Column() {\n      List() {\n        ForEach(this.rows, (row: string) => {\n          ListItem() {\n            Text(row)\n          }\n        })\n      }.listDirection(Axis.Horizontal).height('100%')\n    }\n  }\n}\n"}, 'crate-with-crossnode': {'CodeMaker.ts': "export class CodeMaker {\n  makeCode(): string {\n    return 'ledger-code'\n  }\n}\n", 'ArticleScrollPane.ets': "@Component\nexport struct ArticleScrollPane {\n  @State rows: string[] = []\n  build() {\n    Scroll() {\n      Column() {\n        ForEach(this.rows, (row: string) => {\n          Text(row)\n        })\n      }\n    }.height('100%')\n  }\n}\n", 'CrateLedgerPane.ets': "@Component\nexport struct CrateLedgerPane {\n  @State rows: string[] = []\n  build() {\n    Column() {\n      List() {\n        ForEach(this.rows, (row: string) => {\n          ListItem() {\n            Text(row)\n          }\n        })\n      }.listDirection(Axis.Vertical).height('100%')\n    }\n  }\n}\n", 'CrateAlternatePane.ets': "@Component\nexport struct CrateAlternatePane {\n  @State rows: string[] = []\n  build() {\n    Column() {\n      List() {\n        ForEach(this.rows, (row: string) => {\n          ListItem() {\n            Text(row)\n          }\n        })\n      }.height('100%')\n      List() {}.listDirection(Axis.Vertical)\n    }\n  }\n}\n"}, 'crate-with-conflicting': {'CodeMaker.ts': "export class CodeMaker {\n  makeCode(): string {\n    return 'ledger-code'\n  }\n}\n", 'ArticleScrollPane.ets': "@Component\nexport struct ArticleScrollPane {\n  @State rows: string[] = []\n  build() {\n    Scroll() {\n      Column() {\n        ForEach(this.rows, (row: string) => {\n          Text(row)\n        })\n      }\n    }.height('100%')\n  }\n}\n", 'CrateLedgerPane.ets': "@Component\nexport struct CrateLedgerPane {\n  @State rows: string[] = []\n  build() {\n    Column() {\n      List() {\n        ForEach(this.rows, (row: string) => {\n          ListItem() {\n            Text(row)\n          }\n        })\n      }.listDirection(Axis.Vertical).height('100%')\n    }\n  }\n}\n", 'CrateAlternatePane.ets': "@Component\nexport struct CrateAlternatePane {\n  @State rows: string[] = []\n  build() {\n    Column() {\n      List() {\n        ForEach(this.rows, (row: string) => {\n          ListItem() {\n            Text(row)\n          }\n        })\n      }.listDirection(Axis.Vertical).listDirection(Axis.Horizontal).height('100%')\n    }\n  }\n}\n"}, 'two-subjects': {'CodeMaker.ts': "export class CodeMaker {\n  makeCode(): string {\n    return 'ledger-code'\n  }\n}\n", 'ArticleScrollPane.ets': "@Component\nexport struct ArticleScrollPane {\n  @State rows: string[] = []\n  build() {\n    Scroll() {\n      Column() {\n        ForEach(this.rows, (row: string) => {\n          Text(row)\n        })\n      }\n    }.height('100%')\n  }\n}\n", 'CrateLedgerPane.ets': "@Component\nexport struct CrateLedgerPane {\n  @State rows: string[] = []\n  build() {\n    Column() {\n      List() {\n        ForEach(this.rows, (row: string) => {\n          ListItem() {\n            Text(row)\n          }\n        })\n      }.listDirection(Axis.Vertical).height('100%')\n    }\n  }\n}\n", 'ParcelLedgerPane.ets': "@Component\nexport struct ParcelLedgerPane {\n  @State rows: string[] = []\n  build() {\n    Column() {\n      List() {\n        ForEach(this.rows, (row: string) => {\n          ListItem() {\n            Text(row)\n          }\n        })\n      }.listDirection(Axis.Vertical).height('100%')\n    }\n  }\n}\n"}, 'crate-nominal': {'CodeMaker.ts': "export class CodeMaker {\n  makeCode(): string {\n    return 'ledger-code'\n  }\n}\n", 'ArticleScrollPane.ets': "@Component\nexport struct ArticleScrollPane {\n  @State rows: string[] = []\n  build() {\n    Scroll() {\n      Column() {\n        ForEach(this.rows, (row: string) => {\n          Text(row)\n        })\n      }\n    }.height('100%')\n  }\n}\n", 'CrateNominalPane.ets': "@Component\nexport struct CrateNominalPane {\n  @State rows: CrateRow[] = []\n  build() {\n    Column() {\n      List() {\n        ForEach(this.rows, (row: CrateRow) => {\n          ListItem() {\n            Text(row.caption)\n          }\n        })\n      }.listDirection(Axis.Vertical).height('100%')\n    }\n  }\n}\n"}, 'parcel-nominal': {'CodeMaker.ts': "export class CodeMaker {\n  makeCode(): string {\n    return 'ledger-code'\n  }\n}\n", 'ArticleScrollPane.ets': "@Component\nexport struct ArticleScrollPane {\n  @State rows: string[] = []\n  build() {\n    Scroll() {\n      Column() {\n        ForEach(this.rows, (row: string) => {\n          Text(row)\n        })\n      }\n    }.height('100%')\n  }\n}\n", 'ParcelNominalPane.ets': "@Component\nexport struct ParcelNominalPane {\n  @State rows: ParcelEntry[] = []\n  build() {\n    Column() {\n      List() {\n        ForEach(this.rows, (entry: ParcelEntry) => {\n          ListItem() {\n            Text(entry.title)\n          }\n        })\n      }.listDirection(Axis.Vertical).height('100%')\n    }\n  }\n}\n"}, 'crate-other-annotation': {'CodeMaker.ts': "export class CodeMaker {\n  makeCode(): string {\n    return 'ledger-code'\n  }\n}\n", 'ArticleScrollPane.ets': "@Component\nexport struct ArticleScrollPane {\n  @State rows: string[] = []\n  build() {\n    Scroll() {\n      Column() {\n        ForEach(this.rows, (row: string) => {\n          Text(row)\n        })\n      }\n    }.height('100%')\n  }\n}\n", 'CrateNominalPane.ets': "@Component\nexport struct CrateNominalPane {\n  @State rows: CrateRow[] = []\n  build() {\n    Column() {\n      List() {\n        ForEach(this.rows, (row: AlternativeRow) => {\n          ListItem() {\n            Text(row.caption)\n          }\n        })\n      }.listDirection(Axis.Vertical).height('100%')\n    }\n  }\n}\n"}, 'crate-different-collection': {'CodeMaker.ts': "export class CodeMaker {\n  makeCode(): string {\n    return 'ledger-code'\n  }\n}\n", 'ArticleScrollPane.ets': "@Component\nexport struct ArticleScrollPane {\n  @State rows: string[] = []\n  build() {\n    Scroll() {\n      Column() {\n        ForEach(this.rows, (row: string) => {\n          Text(row)\n        })\n      }\n    }.height('100%')\n  }\n}\n", 'CrateNominalPane.ets': "@Component\nexport struct CrateNominalPane {\n  @State rows: CrateRow[] = []\n  @State backupRows: CrateRow[] = []\n  build() {\n    Column() {\n      List() {\n        ForEach(this.backupRows, (row: CrateRow) => {\n          ListItem() {\n            Text(row.caption)\n          }\n        })\n      }.listDirection(Axis.Vertical).height('100%')\n    }\n  }\n}\n"}, 'crate-unbound-text': {'CodeMaker.ts': "export class CodeMaker {\n  makeCode(): string {\n    return 'ledger-code'\n  }\n}\n", 'ArticleScrollPane.ets': "@Component\nexport struct ArticleScrollPane {\n  @State rows: string[] = []\n  build() {\n    Scroll() {\n      Column() {\n        ForEach(this.rows, (row: string) => {\n          Text(row)\n        })\n      }\n    }.height('100%')\n  }\n}\n", 'CrateNominalPane.ets': "@Component\nexport struct CrateNominalPane {\n  @State rows: CrateRow[] = []\n  @State preview: string = 'preview'\n  build() {\n    Column() {\n      List() {\n        ForEach(this.rows, (row: CrateRow) => {\n          ListItem() {\n            Text(this.preview)\n          }\n        })\n      }.listDirection(Axis.Vertical).height('100%')\n    }\n  }\n}\n"}, 'crate-two-nominal': {'CodeMaker.ts': "export class CodeMaker {\n  makeCode(): string {\n    return 'ledger-code'\n  }\n}\n", 'ArticleScrollPane.ets': "@Component\nexport struct ArticleScrollPane {\n  @State rows: string[] = []\n  build() {\n    Scroll() {\n      Column() {\n        ForEach(this.rows, (row: string) => {\n          Text(row)\n        })\n      }\n    }.height('100%')\n  }\n}\n", 'CrateNominalPane.ets': "@Component\nexport struct CrateNominalPane {\n  @State rows: CrateRow[] = []\n  build() {\n    Column() {\n      List() {\n        ForEach(this.rows, (row: CrateRow) => {\n          ListItem() {\n            Text(row.caption)\n          }\n        })\n      }.listDirection(Axis.Vertical).height('100%')\n    }\n  }\n}\n", 'CrateArchivePane.ets': "@Component\nexport struct CrateArchivePane {\n  @State rows: CrateRow[] = []\n  build() {\n    Column() {\n      List() {\n        ForEach(this.rows, (row: CrateRow) => {\n          ListItem() {\n            Text(row.caption)\n          }\n        })\n      }.listDirection(Axis.Vertical).height('100%')\n    }\n  }\n}\n"}, 'crate-nominal-scroll-competition': {'CodeMaker.ts': "export class CodeMaker {\n  makeCode(): string {\n    return 'ledger-code'\n  }\n}\n", 'ArticleScrollPane.ets': "@Component\nexport struct ArticleScrollPane {\n  @State rows: string[] = []\n  build() {\n    Scroll() {\n      Column() {\n        ForEach(this.rows, (row: string) => {\n          Text(row)\n        })\n      }\n    }.height('100%')\n  }\n}\n", 'CrateNominalPane.ets': "@Component\nexport struct CrateNominalPane {\n  @State rows: CrateRow[] = []\n  build() {\n    Column() {\n      List() {\n        ForEach(this.rows, (row: CrateRow) => {\n          ListItem() {\n            Text(row.caption)\n          }\n        })\n      }.listDirection(Axis.Vertical).height('100%')\n    }\n  }\n}\n", 'CrateAlternatePane.ets': "@Component\nexport struct CrateAlternatePane {\n  @State rows: string[] = []\n  build() {\n    Scroll() {\n      Column() {\n        ForEach(this.rows, (row: string) => {\n          Text(row)\n        })\n      }\n    }.height('100%')\n  }\n}\n"}}


class FrozenVerticalSourcesTests(unittest.TestCase):
    def test_frozen_primitive_and_nominal_sources(self):
        positive_worlds={'crate-single','parcel-single','crate-two','two-subjects',
                         'crate-nominal','parcel-nominal','crate-different-collection','crate-two-nominal'}
        for world,files in FROZEN_SOURCES.items():
            for file,source_text in files.items():
                if file in {'CodeMaker.ts','ArticleScrollPane.ets'}:
                    wanted=set()
                else:
                    wanted={file.rsplit('.',1)[0]}
                with self.subTest(world=world,file=file):
                    result=parse_vertical_list_file(source_text,wanted)
                    if not wanted or world in positive_worlds or file in {'CrateLedgerPane.ets','CrateNominalPane.ets'} and world!='crate-unbound-text' and world not in {'crate-other-annotation'}:
                        self.assertIsNotNone(result)
                    else:self.assertIsNone(result)
