# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,tempfile
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.semantic_ecma import STATE_RE
P=Path(__file__).resolve().parents[1]/'docs/eval/comparison-state-audit/modifier-protocol.json'
class StateDeclarationModifierTests(AgentMemoryTestBase):
    def test_field_prefix_vocabulary_and_keyword_names(self):
        # Same lexical modifier vocabulary as FIELD_RE, not a compiler validator.
        for prefix in ('','private ','public ','protected ','readonly ','private readonly ','protected readonly ','public static readonly '):
            for name in ('expanded','private','public','protected','readonly','static','privateValue'):
                with self.subTest(prefix=prefix,name=name):
                    m=STATE_RE.search('@State '+prefix+name+': boolean = false;')
                    self.assertIsNotNone(m);self.assertEqual(name,m.group(1))
        self.assertEqual('expanded',STATE_RE.search('@State private expanded = false;').group(1))
    def test_existing_single_line_and_unknown_decorator_boundary(self):
        # parse_members passes one physical line; no new multiline/decorator support.
        self.assertIsNone(STATE_RE.search('@State'))
        self.assertIsNone(STATE_RE.search('private expanded: boolean = false;'))
        self.assertIsNone(STATE_RE.search('@Unknown private expanded: boolean = false;'))
        self.assertIsNone(STATE_RE.search('@State() private expanded: boolean = false;'))
        # Existing substring scanning is not silently advertised as lexical masking.
        self.assertIsNotNone(STATE_RE.search("const text = '@State private expanded: boolean';"))
    def test_public_state_identity_and_edges_use_actual_field(self):
        protocol=json.loads(P.read_text())
        for modifier,source in protocol['sources'].items():
            with self.subTest(modifier=modifier),tempfile.TemporaryDirectory() as d:
                root=Path(d);(root/'DisclosureState.ets').write_text(source)
                self.run_memory(root,'init');self.run_memory(root,'learn-path','--path','.')
                symbols=json.loads(self.run_memory(root,'list','--type','code-symbol','--limit','100','--json').stdout)
                edges=json.loads(self.run_memory(root,'list','--type','memory-edge','--limit','100','--json').stdout)
                states=[s for s in symbols if s['symbol_type']=='state']
                self.assertEqual(['expanded'],[s['symbol'] for s in states]);state=states[0]
                self.assertEqual('DisclosureState.expanded',state['qualified_name'])
                self.assertEqual((2,2),(state['start_line'],state['end_line']))
                self.assertEqual('state',state['symbol_type'])
                matched={e['relation'] for e in edges if e['target_type']=='code_symbol' and e['target_id']==state['id']}
                self.assertTrue({'reads_state','writes_state'}<=matched)
    def test_same_field_name_in_distinct_owners_does_not_merge(self):
        source=''
        for owner in ('FirstPanel','SecondPanel'):
            source+=f'export class {owner} {{\n @State private expanded: boolean = false;\n flip(): void {{\n this.expanded = !this.expanded;\n }}\n}}\n'
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'Panels.ets').write_text(source)
            self.run_memory(root,'init');self.run_memory(root,'learn-path','--path','.')
            symbols=json.loads(self.run_memory(root,'list','--type','code-symbol','--limit','100','--json').stdout)
            edges=json.loads(self.run_memory(root,'list','--type','memory-edge','--limit','100','--json').stdout)
            byid={s['id']:s for s in symbols};states=[s for s in symbols if s['symbol_type']=='state']
            self.assertEqual({'FirstPanel.expanded','SecondPanel.expanded'},{s['qualified_name'] for s in states})
            observed=set()
            for e in edges:
                if e['relation'] not in {'reads_state','writes_state'} or e['source_type']!='code_symbol' or e['target_type']!='code_symbol':continue
                a,b=byid[e['source_id']],byid[e['target_id']]
                self.assertEqual(a['qualified_name'].split('.')[0],b['qualified_name'].split('.')[0]);observed.add(b['qualified_name'])
            self.assertEqual({'FirstPanel.expanded','SecondPanel.expanded'},observed)
