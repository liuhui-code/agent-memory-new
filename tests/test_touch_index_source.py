"""Frozen synthetic source bytes only; no evidence-output dependency."""
import json
from pathlib import Path
import unittest
from tools.agent_memory_runtime.ui_touch_index_source import parse_touch_index_file

F=json.loads((Path(__file__).parent/'fixtures/touch_index_source.json').read_text())
BASE=F['sources']['original-one-positive']['CanvasTouchPane.ets']


class TouchIndexSourceTests(unittest.TestCase):
    def test_frozen_positive_zero_and_two_complete_ranges(self):
        for file,source in F['sources']['original-two-positive'].items():
            result=parse_touch_index_file(source);self.assertIsNotNone(result)
            proof=next(iter(result.values()))
            self.assertEqual((proof['owner_start'],proof['owner_end']),(2,10))
            self.assertEqual((proof['build_start'],proof['build_end']),(4,9))
            self.assertEqual((proof['callback_start'],proof['callback_end']),(5,8))
            self.assertEqual(proof['callback_name'],'onTouch')
            self.assertEqual(proof['literal_index'],2 if file.startswith('Timeline')else 0)
    def test_three_four_and_mixed_not_capacity_logic_in_parser(self):
        for cohort,count in [('supplement-three-positive',3),('supplement-four-positive',4),('supplement-positive-plus-unknown',2)]:
            known=[p for source in F['sources'][cohort].values()if(p:=parse_touch_index_file(source))is not None]
            self.assertEqual(len(known),count)
    def test_unknown_controls_and_type_shadow(self):
        for cohort,sources in F['sources'].items():
            if any(word in cohort for word in ('length-only','quoted-read','wrong-parameter','shadowed','external-read','guarded','dynamic-index','annotation-')):
                for file,source in sources.items():
                    with self.subTest(cohort=cohort,file=file):self.assertIsNone(parse_touch_index_file(source))
    def test_optional_state_entry_export_and_empty_stack(self):
        for decorators in ('@Component','@Entry\n@Component'):
            for export in ('export ',''):
                for state in ('','@State '):
                    source=BASE.replace('@Component',decorators).replace('export ',export).replace(' horizontal:', ' '+state+'horizontal:').replace("Text('surface')",'')
                    self.assertIsNotNone(parse_touch_index_file(source))
    def test_arbitrary_identifier_binding_and_multi_declarations(self):
        source=BASE.replace('CanvasTouchPane','_View$').replace('horizontal','_pos$').replace('sample','_evt$').replace('contact','_hit$')
        self.assertIsNotNone(parse_touch_index_file(source))
        second=BASE.replace('CanvasTouchPane','OtherPane')
        self.assertEqual(set(parse_touch_index_file(BASE+second)),{'CanvasTouchPane','OtherPane'})
        self.assertIsNone(parse_touch_index_file(BASE+BASE))
    def test_canonical_nonnegative_integer_only(self):
        for value in ('0','1','2','999'):
            self.assertEqual(next(iter(parse_touch_index_file(BASE.replace('touches[0]','touches['+value+']')).values()))['literal_index'],int(value))
        for value in ('00','01','-1','+2','2.0','2e0','0x2','selected','sample.touches.length','0_1'):
            with self.subTest(value=value):self.assertIsNone(parse_touch_index_file(BASE.replace('touches[0]','touches['+value+']')))
    def test_binding_and_scope_fail_closed(self):
        for old,new in [('sample.touches','other.touches'),('const contact','const sample'),('= contact.x','= sample.x'),('this.horizontal','this.other'),('contact.x','contact.y'),('TouchEvent','OtherEvent'),('Stack()','OtherStack()')]:
            self.assertIsNone(parse_touch_index_file(BASE.replace(old,new)))
        self.assertIsNone(parse_touch_index_file('class TouchEvent {}\n'+BASE))
        self.assertIsNone(parse_touch_index_file("import { Other as TouchEvent } from './other'\n"+BASE))
    def test_noncode_and_unknown_lexical_content(self):
        self.assertIsNotNone(parse_touch_index_file('// struct TouchEvent {}\n'+BASE.replace("'surface'","'sample.touches[5] struct TouchEvent {}'")))
        for source in (BASE[:-2],BASE.replace('contact.x','contact.x + 1'),BASE.replace("'surface'",'`surface ${sample}`'),BASE.replace("'surface'","'\\q'"),BASE+' const x = /touches[0]/\n'):
            self.assertIsNone(parse_touch_index_file(source))
    def test_statement_separator_required(self):
        self.assertIsNotNone(parse_touch_index_file(BASE.replace('touches[0]\n','touches[0];\n').replace('contact.x\n','contact.x;\n')))
        self.assertIsNone(parse_touch_index_file(BASE.replace('touches[0]\n   this','touches[0] this')))
