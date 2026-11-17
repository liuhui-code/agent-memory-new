# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json
import unittest
from pathlib import Path
from tools.agent_memory_runtime.validation_field_source import parse_validation_field_file

F=json.loads((Path(__file__).parent/'fixtures/validation_field_source.json').read_text())
BASE=F['sources']['existing-three-mixed']['ProfileEntry.ts']
OBJ=F['sources']['existing-three-mixed']['PurchaseEntry.ts']

class ValidationFieldSourceTests(unittest.TestCase):
    def test_frozen_complete_sources(self):
        for world,sources in F['sources'].items():
            for file,source in sources.items():
                with self.subTest(world=world,file=file):
                    proofs=parse_validation_field_file(source)
                    self.assertIsNotNone(proofs)
                    wanted=[r for r in F['expected'][world] if r['file']==file]
                    self.assertEqual(len(proofs),len(wanted))
                    for proof,e in zip(proofs,wanted):
                        for k in ('owner','method','start_line','end_line','root','dispatch_argument'):self.assertEqual(proof[k],e[k])
                        self.assertEqual(proof['field'],e['guarded_member'])
                        self.assertIn(proof['kind'],('class','struct'))
    def test_scalar_and_containing_object_both_qualify(self):
        for source in (OBJ,OBJ.replace('this.dispatchPurchase(draft)','this.dispatchPurchase(draft.customerCode)').replace('private dispatchPurchase(draft: PurchaseDraft)', 'private dispatchPurchase(value: string)')):
            self.assertEqual(len(parse_validation_field_file(source)),1)
    def test_component_state_not_required_or_preferred(self):
        s=BASE.replace('export class','@Entry\n@Component\nexport struct').replace("  displayName:","  @State displayName:")
        p=parse_validation_field_file(s)[0];self.assertEqual(p['kind'],'struct');self.assertEqual(p['owner_start'],3)
        self.assertEqual(parse_validation_field_file(BASE)[0]['field'],p['field'])
    def test_lexical_unknowns_whole_file(self):
        for tail in ('\nconst x = /a/','\nconst x = `text`','\nunknown!', '\nnamespace X {}','\nclass X {', '\nclass X extends ProfileEntry {}'):
            with self.subTest(tail=tail):self.assertIsNone(parse_validation_field_file(BASE+tail))
    def test_guard_mutation_binding_and_order_unknown(self):
        for s in (BASE.replace('=== 0','=== 1'),BASE.replace('return\n','if (true) { return }\n'),BASE.replace('    this.dispatchProfile','    this.displayName = \'new\'\n    this.dispatchProfile'),BASE.replace('this.dispatchProfile(this.displayName)','this.dispatchProfile(this.other)'),BASE.replace('this.dispatchProfile(this.displayName)','this.dispatchProfile(this)'),BASE.replace('this.dispatchProfile(this.displayName)',''),BASE.replace('this.displayName.trim()','this.displayName?.trim()'),BASE.replace('this.dispatchProfile(this.displayName)','this.redispatcher(this.displayName)').replace('private dispatchProfile','private redispatcher')):
            with self.subTest(source=s):self.assertIsNone(parse_validation_field_file(s))
    def test_duplicates_shadows_and_unknown_auxiliary(self):
        for s in (BASE.replace("  displayName: string = ''", "  displayName: string = ''\n  displayName: string = ''"),BASE.replace('submitProfile()','submitProfile(displayName: string)'),BASE.replace('ProfileEntry','promptAction'),BASE.replace('void {}','void { unknown() }'),OBJ.replace('customerCode: string','customerCode: number'),OBJ.replace('draft: PurchaseDraft','draft: MissingType')):
            with self.subTest(source=s):self.assertIsNone(parse_validation_field_file(s))
    def test_comment_string_not_source_and_exact_identifiers_retained(self):
        s=BASE.replace('displayName','oldDisplayName').replace("'Please supply a value'","'displayName === 0'")
        p=parse_validation_field_file(s)[0];self.assertEqual(p['field'],'oldDisplayName')
        self.assertEqual(parse_validation_field_file('// '+BASE.replace('\n','\n// ')),[])
    def test_unknown_trailing_statement_not_dropped(self):
        for tail in ('this.displayName = \'x\'','return','if (true) {}','this.dispatchProfile(this.displayName)\n    this.dispatchProfile(this.displayName)\n    this.dispatchProfile(this.displayName)'):
            s=BASE.replace('    this.dispatchProfile(this.displayName)','    this.dispatchProfile(this.displayName)\n    '+tail)
            self.assertIsNone(parse_validation_field_file(s))
    def test_nonpositive_known_auxiliary(self):
        self.assertEqual(parse_validation_field_file('class Helper { empty(): void {} }'),[])
        self.assertEqual(parse_validation_field_file('class Helper { report(): void { console.info(\'text\') } }'),[])
    def test_limits_and_wrong_input(self):
        self.assertIsNone(parse_validation_field_file(None))
        self.assertIsNone(parse_validation_field_file(' '* (2*1024*1024+1)))

    def test_token_and_global_identity_boundaries(self):
        for source in (BASE.replace('===','= = ='),BASE.replace('===','=/* gap */=='),BASE+'\nclass console {}',BASE.replace("  displayName: string = ''", "  displayName: string = ''\n  service: MissingService = new MissingService()"), '\ud800'):
            with self.subTest(source=source):self.assertIsNone(parse_validation_field_file(source))

    def test_statement_boundaries_invalid_adjacent_tokens(self):
        bad=[BASE.replace(" })\n      return", " })return"),
             BASE.replace('    this.dispatchProfile(this.displayName)', '    this.dispatchProfile(this.displayName)this.dispatchProfile(this.displayName)'),
             BASE.replace("  displayName: string = ''", "  displayName: string = '' other: string = ''")]
        for source in bad:
            with self.subTest(source=source):self.assertIsNone(parse_validation_field_file(source))

    def test_statement_boundaries_explicit_semicolon_same_line(self):
        good=[BASE.replace(" })\n      return", " }); return"),
              BASE.replace('    this.dispatchProfile(this.displayName)', '    this.dispatchProfile(this.displayName); this.dispatchProfile(this.displayName);'),
              BASE.replace("  displayName: string = ''", "  displayName: string = ''; other: string = ''; ")]
        for source in good:
            with self.subTest(source=source):self.assertEqual(len(parse_validation_field_file(source)),1)

    def test_typed_literal_auxiliary_returns(self):
        for typ,value in [('string',"'notes'"),('number','4'),('boolean','true')]:
            source=BASE.replace('  private dispatchProfile',f'  describe(): {typ} {{ return {value} }}\n  private dispatchProfile')
            with self.subTest(typ=typ):self.assertEqual(len(parse_validation_field_file(source)),1)

    def test_typed_auxiliary_unknowns(self):
        for declaration in ("describe(): string { return 4 }", "describe() { return 'notes' }", "async describe(): Promise<string> { return 'notes' }", "describe(): string { return 'a' + 'b' }", "describe(): string { return 'a'; return 'b' }", "describe(): string { return\n 'notes' }", "async describe(): string { return 'notes' }", "describe(): boolean { return null }", "describe(): string {}"):
            source=BASE.replace('  private dispatchProfile','  '+declaration+'\n  private dispatchProfile')
            with self.subTest(declaration=declaration):self.assertIsNone(parse_validation_field_file(source))
        self.assertIsNone(parse_validation_field_file(BASE.replace('submitProfile(): void','submitProfile(): string')))

    def test_void_auxiliary_return_newline_is_not_literal_return(self):
        for gap in ('\n', '\n/* comment */ ', '/*\ncomment */ '):
            source=BASE.replace('void {}', "void { return"+gap+"'notes' }")
            with self.subTest(gap=gap):self.assertIsNone(parse_validation_field_file(source))
        # Corrected development oracle: void cannot return a value; only typed auxiliaries may.
        self.assertEqual(len(parse_validation_field_file(BASE)),1)

    def test_void_auxiliary_value_rejected(self):
        for literal in ("'notes'", '4', 'true', 'null'):
            source=BASE.replace('void {}', 'void { return '+literal+'; }')
            with self.subTest(literal=literal):self.assertIsNone(parse_validation_field_file(source))
