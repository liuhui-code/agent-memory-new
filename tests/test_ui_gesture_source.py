import unittest
from tools.agent_memory_runtime.ui_gesture_source import parse_gesture_file

BASE = """@Component
export struct TilePanSurface {
  @State dragOffset: number = 0

  build() {
    Stack() {}
      .gesture(
        PanGesture().onActionUpdate((sample: GestureEvent) => {
          this.dragOffset = sample.offsetX
        })
      )
  }
}
"""
HELP = """@Component
export struct TileGestureHelp {
  build() {
    Column() {
      Text('Tile gesture interaction')
      Text('Stack().gesture(PanGesture().onActionUpdate(callback))')
    }
  }
}
"""
STATE = """export interface TileState {
  count: number
  progress: number
  pieces: number[]
}
"""
FORWARD = BASE.replace('@State dragOffset: number = 0', 'private mover: TileMover = new TileMover()').replace(
    'this.dragOffset = sample.offsetX', 'this.mover.move(sample.offsetY)')
REG = """Stack() {}
      .gesture(
        PanGesture().onActionUpdate((sample: GestureEvent) => {
          this.dragOffset = sample.offsetX
        })
      )"""


class UiGestureSourceTests(unittest.TestCase):
    def parse(self, source=BASE, names=('TilePanSurface',)):
        return parse_gesture_file(source, names)

    def reject(self, *sources, names=('TilePanSurface',)):
        for source in sources:
            with self.subTest(source=source):
                self.assertIsNone(self.parse(source, names))

    def test_exact_owner_build_callback_and_source_offsets(self):
        frame = self.parse()['TilePanSurface']
        self.assertEqual((frame['owner_start'], frame['owner_end'], frame['build_start'], frame['build_end']), (2, 13, 5, 12))
        self.assertTrue(frame['positive'])
        site = frame['sites'][0]
        self.assertEqual((site['callback_start'], site['callback_end']), (8, 10))
        self.assertEqual((site['action_kind'], site['param'], site['target'], site['member']),
                         ('assignment', 'sample', 'dragOffset', 'offsetX'))
        self.assertEqual(BASE[site['callback_start_offset']:site['callback_end_offset']],
                         'onActionUpdate((sample: GestureEvent) => {\n          this.dragOffset = sample.offsetX\n        }')
        encoded = BASE.encode('utf-8')[site['callback_start_byte']:site['callback_end_byte']]
        self.assertEqual(encoded.decode(), BASE[site['callback_start_offset']:site['callback_end_offset']])

    def test_forwarding_one_two_three_arguments_and_unresolved_type(self):
        for args in ('sample.offsetY', 'sample.offsetX, sample.offsetY', 'sample.offsetX, sample.offsetY, sample.speed'):
            source = FORWARD.replace('sample.offsetY)', args + ')')
            site = self.parse(source)['TilePanSurface']['sites'][0]
            self.assertEqual(site['action_kind'], 'forwarding')
            self.assertEqual(site['target'], 'mover')
            self.assertEqual(site['method'], 'move')
            self.assertEqual(len(site['args']), args.count(',') + 1)
            self.assertEqual(site['target_definition']['type_name'], 'TileMover')
        board = FORWARD.replace('TilePanSurface', 'BoardGestureSurface').replace('TileMover', 'BoardEngine').replace('mover', 'boardEngine').replace('.move(', '.shift(')
        self.assertTrue(self.parse(board, ('BoardGestureSurface',))['BoardGestureSurface']['positive'])

    def test_parameter_binding_and_optional_annotation(self):
        for source in (BASE.replace('sample', 'drag'), BASE.replace(': GestureEvent', '')):
            self.assertTrue(self.parse(source)['TilePanSurface']['positive'])
        self.reject(BASE.replace('sample.offsetX', 'other.offsetX'), BASE.replace('(sample: GestureEvent)', '(this: GestureEvent)'),
                    BASE.replace('(sample: GestureEvent)', '(PanGesture: GestureEvent)'),
                    BASE.replace('(sample: GestureEvent)', 'sample'), BASE.replace('(sample: GestureEvent)', '(sample: OtherEvent)'),
                    BASE.replace('(sample: GestureEvent)', '(sample = other)'), BASE.replace('(sample: GestureEvent)', '(...sample)'),
                    BASE.replace('(sample: GestureEvent)', '({ offsetX })'))

    def test_fields_are_exact_owned_declared_targets(self):
        self.reject(BASE.replace('this.dragOffset', 'this.missing'), FORWARD.replace('this.mover.move', 'this.missing.move'),
                    FORWARD.replace('new TileMover()', 'new OtherMover()'),
                    BASE.replace('this.dragOffset = sample.offsetX', 'this.dragOffset.move(sample.offsetX)'),
                    FORWARD.replace('this.mover.move(sample.offsetY)', 'this.mover = sample.offsetY'))
        # Declarations may follow build: relation is resolved after full members.
        state = '  @State dragOffset: number = 0\n'
        after = BASE.replace(state, '').replace('\n}\n', '\n' + state + '}\n')
        self.assertTrue(self.parse(after)['TilePanSurface']['positive'])

    def test_nonmatch_help_and_interface_manifest(self):
        scan = self.parse(BASE + HELP + STATE, ('TilePanSurface', 'TileGestureHelp', 'TileState'))
        self.assertTrue(scan['TilePanSurface']['positive'])
        self.assertFalse(scan['TileGestureHelp']['positive'])
        self.assertFalse(scan['TileState']['positive'])
        self.assertEqual(scan['TileState']['kind'], 'interface')
        self.assertIsNone(scan['TileState']['build_start'])
        self.assertEqual(set(scan.declared_names), {'TilePanSurface', 'TileGestureHelp', 'TileState'})
        partial = self.parse(BASE + HELP + STATE)
        self.assertEqual(set(partial), {'TilePanSurface'})
        self.assertEqual(len(partial.declarations), 3)
        self.assertEqual(partial.declarations[-1]['kind'], 'interface')

    def test_interface_grammar_is_closed_and_fields_unique(self):
        self.reject(STATE.replace('pieces: number[]', 'pieces: Object'), STATE.replace('count: number', 'count: number\n  count: number'),
                    STATE.replace('count: number', 'count(): number'), STATE.replace('count: number', '["count"]: number'),
                    STATE.replace('interface TileState', 'interface TileState extends Other'),
                    STATE.replace('count: number\n  progress', 'count: number progress'), names=('TileState',))
        for source in (STATE.replace('count: number', 'count: number;'), 'export interface TileState { count: number }'):
            self.assertFalse(self.parse(source, ('TileState',))['TileState']['positive'])
        all_types = 'export interface TileState { count: number; ready: boolean; label: string; pieces: number[] }'
        self.assertFalse(self.parse(all_types, ('TileState',))['TileState']['positive'])

    def test_literals_and_comments_cannot_create_registration(self):
        help_source = HELP.replace("Text('Tile gesture interaction')", "Text('gesture PanGesture onActionUpdate') /* Stack().gesture(bad) */")
        self.assertFalse(self.parse(help_source, ('TileGestureHelp',))['TileGestureHelp']['positive'])
        self.assertTrue(self.parse(BASE.replace('Stack() {}', 'Stack() { /* not a real child */ }'))['TilePanSurface']['positive'])
        unicode_source = BASE.replace('  build()', "  // 中文 annotation\n  build()")
        site = self.parse(unicode_source)['TilePanSurface']['sites'][0]
        self.assertEqual(unicode_source.encode()[site['callback_start_byte']:site['callback_end_byte']].decode(),
                         unicode_source[site['callback_start_offset']:site['callback_end_offset']])

    def test_computed_optional_rejection_precedes_nonmatch(self):
        for expression in ("this['gesture'](handler)", 'this["ges\\u0074ure"](handler)',
                           'this[selector](handler)', 'this?.gesture(handler)', 'Text(["gesture"])'):
            self.reject(HELP.replace('    Column()', '    ' + expression + '\n    Column()'), names=('TileGestureHelp',))
        self.reject(BASE.replace('this.dragOffset', "this['dragOffset']"))

    def test_lexical_unknown_before_any_certificate(self):
        for value in ("Text('line\nstring')", 'Text("line\nstring")', 'Text(`plain`)', 'Text(`${sample}`)',
                      'Text(/gesture/)', 'Pan\\u0047esture()', '/* open', 'Text(?)'):
            self.reject(HELP.replace('    Column()', value + '\n    Column()'), names=('TileGestureHelp',))
        self.reject(BASE.replace('\n', '\r'), BASE.replace('\n', '\u2028'), BASE[:-3])
        self.assertEqual(self.parse(BASE.replace('\n', '\r\n'))['TilePanSurface']['build_start'], 5)

    def test_class_helper_import_and_custom_shadow_never_disappear(self):
        self.reject('function PanGesture() { return {} }\n' + BASE,
                    "import { PanGesture } from './custom'\n" + BASE,
                    BASE + 'export class TileCustom { gesture() {} }\n', BASE + 'function TileHelper() {}\n',
                    BASE + 'type TileAlias = number\n', BASE + BASE.replace('TilePanSurface', 'Stack'),
                    BASE.replace('dragOffset: number', 'Stack: number'), names=('TilePanSurface',))
        self.reject(HELP.replace('    Column()', '    const Stack = another\n    Column()'),
                    HELP.replace('    Column()', '    function Stack() {}\n    Column()'), names=('TileGestureHelp',))

    def test_positive_chain_closure_and_unknown_handlers(self):
        self.reject(BASE.replace('Stack()', 'Row()'), BASE.replace('Stack() {}', 'Stack() { Text("child") }'),
                    BASE.replace('PanGesture()', 'TapGesture()'), BASE.replace('PanGesture()', 'CustomGesture()'),
                    BASE.replace('PanGesture()', 'PanGesture(1)'), BASE.replace('.onActionUpdate', '.onActionEnd'),
                    BASE.replace('.onActionUpdate', '.onActionUpdate(handler).onActionUpdate'),
                    BASE.replace('((sample: GestureEvent) => {\n          this.dragOffset = sample.offsetX\n        })', '(handler)'),
                    BASE.replace('Stack() {}', 'Stack() {}.width(5)'))

    def test_callback_member_presence_and_single_statement(self):
        for replacement in ('this.dragOffset = sample.offsetX; Text("extra")',
                            'this.dragOffset = this.normalize(sample.offsetX)', 'this.dragOffset = sample.offsetX + 1',
                            'this.dragOffset = sample.offsetX "ignored"', 'return sample.offsetX',
                            'this.dragOffset = sample.offsetX;;', 'this.dragOffset = sample.offsetX, sample.offsetY'):
            self.reject(BASE.replace('this.dragOffset = sample.offsetX', replacement))
        self.reject(FORWARD.replace('sample.offsetY)', 'sample.a, sample.b, sample.c, sample.d)'),
                    FORWARD.replace('sample.offsetY)', 'sample.offsetY,)'))
        self.assertTrue(self.parse(BASE.replace('sample.offsetX\n', 'sample.offsetX;\n'))['TilePanSurface']['positive'])

    def test_members_presence_types_and_end_boundaries(self):
        self.reject(BASE.replace('  @State', '  "ignored"\n  @State', 1), BASE.replace('  build()', '  "ignored" build()'),
                    BASE.replace('\n}\n', '\n  "ignored"\n}\n'), BASE.replace('  build()', '  extra() {}\n  build()'),
                    BASE.replace('  build()', '  build() {}\n  build()'),
                    BASE.replace('number = 0', 'number = "zero"'), BASE.replace('number = 0', 'boolean = "true"'),
                    BASE.replace('number = 0', 'number = 01'), BASE.replace('number = 0', 'number = ' + '9' * 33),
                    BASE.replace('  build()', '  @State dragOffset: number = 1\n  build()'),
                    BASE.replace('number = 0\n', 'number = 0 @State extra: number = 1\n'))
        self.assertTrue(self.parse(BASE.replace('number = 0\n', 'number = 0;\n'))['TilePanSurface']['positive'])
        self.reject(BASE.replace('  build()', '  private dragOffset: TileMover = new TileMover()\n  build()'),
                    BASE.replace('  build()', '  @State this: number = 0\n  build()'))

    def test_multiple_sites_owners_and_registration_end(self):
        body = BASE.replace(REG, REG + '\n    ' + REG)
        self.assertEqual(len(self.parse(body)['TilePanSurface']['sites']), 2)
        body_semi = BASE.replace(REG, REG + '; ' + REG)
        self.assertEqual(len(self.parse(body_semi)['TilePanSurface']['sites']), 2)
        self.reject(BASE.replace(REG, REG + ' ' + REG))
        one_line = 'Stack() {}.gesture(PanGesture().onActionUpdate((sample) => { this.dragOffset = sample.x }))'
        self.reject(BASE.replace(REG, one_line + '; ' + one_line))
        scan = self.parse(BASE + BASE.replace('TilePanSurface', 'TileSecond'), ('TilePanSurface', 'TileSecond'))
        self.assertEqual(len(scan), 2)
        self.assertTrue(all(f['positive'] for f in scan.values()))
        self.reject(BASE + BASE)
        self.assertIsNone(self.parse(BASE, ('Missing',)))


if __name__ == '__main__':
    unittest.main()
