# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json
from pathlib import Path
import unittest
from tools.agent_memory_runtime.query_builder_witness import direct_chain_witness

class BuilderModifierWitnessTests(unittest.TestCase):
    def witness(self,body,header='paintSurface() {'):
        source='@Component\nstruct Sample {\n  @Builder\n  '+header+'\n'+body+'\n  }\n}\n'
        return direct_chain_witness(source.encode(),{'symbol':'paintSurface','start_line':4,'end_line':len(source.splitlines())-1},('padding','backgroundColor'))

    def test_thirteen_frozen_sources(self):
        p=Path(__file__).parents[1]/'docs/evidence/builder-chinese-consumer/protocol.json'
        for c in json.loads(p.read_text())['source_controls']:
            lines=c['source'].splitlines()
            end=next((i for i,l in enumerate(lines)if l=='  build() {'),max(i+1 for i,l in enumerate(lines)if l=='  }'))
            with self.subTest(case=c['id']):
                self.assertEqual(bool(direct_chain_witness(c['source'].encode(),{'symbol':'paintSurface','start_line':4,'end_line':end},c['required'])),c['witness'])

    def test_true_header_body_not_parameter_or_type_brace(self):
        self.assertTrue(self.witness('    Column().padding(1).backgroundColor(x)', 'paintSurface(options: {value: number}): {flag: boolean} {'))

    def test_malformed_header_does_not_gain_witness(self):
        self.assertIsNone(self.witness('    Column().padding(1).backgroundColor(x)', 'paintSurface(x: { a: number ) {'))
        self.assertIsNone(self.witness('    Column().padding(1).backgroundColor(x)', "'junk' paintSurface() {"))

    def test_top_level_literals_never_become_whitespace(self):
        for body in ["    Column() 'unexpected' .padding(1).backgroundColor(x)","    Column().padding(1).backgroundColor(x)\n    'unexpected'",'    Column().padding(1).backgroundColor(x) `opaque`']:
            with self.subTest(body=body):self.assertIsNone(self.witness(body))
        self.assertTrue(self.witness("    Column('argument').padding(1).backgroundColor('value')"))

    def test_complete_body_and_separators(self):
        for body in ['    Column().padding(1).backgroundColor(x)\n    return other','    Column().padding(1).backgroundColor(x)Row()','    Column().padding(1).backgroundColor(x);.width(1)','    if (ready) {}\n    .padding(1).backgroundColor(x)','    new Column().padding(1).backgroundColor(x)']:
            with self.subTest(body=body):self.assertIsNone(self.witness(body))
        self.assertTrue(self.witness('    Column()\n    .padding(1)\n    .backgroundColor(x);\n    Row()'))
        self.assertTrue(self.witness('    Column().padding(1).backgroundColor(x) /* comment */;'))

    def test_nested_cannot_supply_outer_pair(self):
        self.assertIsNone(self.witness('    Column() {\n      Text().backgroundColor(x)\n    }.padding(1)'))
        self.assertIsNone(self.witness('    Column(() => Text().backgroundColor(x)).padding(1)'))
        self.assertTrue(self.witness('    Column() {\n      ForEach(xs, (x) => { Text(x) })\n    }.padding(1).backgroundColor(x)'))

    def test_unknown_receiver_or_delimiters(self):
        for body in ['    obj[key]\n    .render().padding(1).backgroundColor(x)','    foo?.Column().padding(1).backgroundColor(x)','    Column([)]).padding(1).backgroundColor(x)','    function Paint() {}\n    .padding(1).backgroundColor(x)','    {}\n    .padding(1).backgroundColor(x)']:
            with self.subTest(body=body):self.assertIsNone(self.witness(body))

class BuilderModifierBindingTests(unittest.TestCase):
    def setUp(self):
        import tempfile,hashlib
        from types import SimpleNamespace
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.source=b'@Builder\nfunction part() { Column().padding(1).backgroundColor(x) }\n'
        (self.root/'Parts.ets').write_bytes(self.source)
        self.project=SimpleNamespace(root=self.root,project_id='p')
        self.row=dict(id=1,project_id='p',file_path='Parts.ets',symbol='part',symbol_key='key',qualified_name='part',start_line=2,end_line=2,source_digest=hashlib.sha256(self.source).hexdigest(),index_generation=1,symbol_type='function',evidence_class='static',semantic_adapter='arkts-static@1.2',callable_roles='["arkts_builder"]')
        self.query='请返回设置内边距和背景颜色的 Builder 源码。'
    def tearDown(self):self.tmp.cleanup()
    def bound(self,ranked=None,selected=None):
        from tools.agent_memory_runtime.query_builder_selection import bind_localization
        ranked=ranked or [self.row]
        selected=ranked if selected is None else selected
        result={'callable_candidates':[dict(r,symbol_id=r['id']) for r in ranked]}
        return bind_localization(self.project,self.query,ranked,selected,result)
    def test_source_bound_evidence_and_transport(self):
        from tools.agent_memory_runtime.query_builder_selection import project_builder_evidence,builder_anchors,MARKER
        evidence=project_builder_evidence(self.bound(),{})
        self.assertEqual(evidence[MARKER]['required_calls'],['padding','backgroundColor'])
        self.assertFalse(evidence[MARKER]['behavior_certified'])
        anchors=[{'file_path':'Other.ets'}]
        self.assertEqual(builder_anchors(anchors,evidence,False,self.query)[0]['symbol'],'part')
        self.assertEqual(builder_anchors(anchors,json.loads(json.dumps(evidence)),False,self.query),anchors)
        self.assertEqual(builder_anchors(anchors,evidence,True,self.query),anchors)
        self.assertEqual(builder_anchors([{'graph_neighbor':True}],evidence,False,self.query),[{'graph_neighbor':True}])
    def test_malformed_and_rebound_proofs_fail_closed(self):
        from tools.agent_memory_runtime.query_builder_selection import project_builder_evidence
        for value in [(),None,'bad',{},([],()),(None,()),(object(),[])]:
            local=self.bound();local._modifier=value;old={}
            self.assertIs(project_builder_evidence(local,old),old)
        local=self.bound();local._query=self.query.replace('设置','配置');old={}
        self.assertIs(project_builder_evidence(local,old),old)
        local=self.bound();local._rows[0]['source_digest']='0'*64
        self.assertIs(project_builder_evidence(local,old),old)
    def test_full_known_pool_identity_selected_and_cap(self):
        from tools.agent_memory_runtime.query_builder_selection import BuilderLocalization
        other=dict(self.row,id=2,symbol_key='other')
        self.assertNotIsInstance(self.bound([self.row,other],[self.row]),BuilderLocalization)
        malformed=dict(other,source_digest='')
        self.assertNotIsInstance(self.bound([self.row,malformed]),BuilderLocalization)
        rows=[dict(self.row,id=i,symbol_key=str(i))for i in range(1,5)]
        self.assertNotIsInstance(self.bound(rows),BuilderLocalization)
        (self.root/'Parts.ets').write_bytes(self.source+b'// changed')
        self.assertNotIsInstance(self.bound(),BuilderLocalization)
    def test_negative_exclusion_and_no_positive_fallback(self):
        from tools.agent_memory_runtime.query_builder_selection import BuilderLocalization
        self.query=self.query[:-1]+'，不要返回卡片。'
        self.row['owner_name']='Card'
        self.assertNotIsInstance(self.bound(),BuilderLocalization)
