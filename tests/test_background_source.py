# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,unittest
from pathlib import Path
from tools.agent_memory_runtime.query_background_source import parse_background_source
from tools.agent_memory_runtime.query_render_recall import parse_render_request,recall_projection
P=json.loads((Path(__file__).parents[1]/'docs/evidence/rebuild-visual09-20261115/protocol.json').read_text())
SOURCE=P['sources']['AmountSurface.ets'];Q=P['queries'][0][1]
class BackgroundSourceTests(unittest.TestCase):
 def test_positive_renamed_comments_crlf_and_numeric_field(self):
  for source in [SOURCE,SOURCE.replace('AmountSurface','OtherPanel').replace('Category picker','Options').replace('Amount','Size'),SOURCE.replace('\n','\r\n'),SOURCE.replace(' build()', ' @State count: number = 0\n build()'),SOURCE.replace('.backgroundColor','/* background property */.backgroundColor')]:
   with self.subTest(source=source):
    p=parse_background_source(source);self.assertIsNotNone(p);self.assertEqual((p['build_start'],p['build_end']),(4,11)if '@State' in source else (3,10))
 def test_unknown_non_modifier_shadowing_callback_and_mixed_source(self):
  variants=[SOURCE.replace('.backgroundColor(Color.White)',''),SOURCE.replace('.backgroundColor(Color.White)',".width('backgroundColor')"),SOURCE.replace('AmountSurface','Color'),SOURCE.replace('AmountSurface','Text'),SOURCE.replace(' build()', ' Color: string = "white"\n build()'),SOURCE.replace('Color.White','this.color'),SOURCE.replace('Color.White','getColor()'),SOURCE.replace('.shadow({ radius: 7 })','.onClick(() => { this.paint() })'),SOURCE.replace(' build()', ' helper(): string { return "backgroundColor" }\n build()'),SOURCE+'\nexport class Other {}',SOURCE.replace("'Amount'",'`Amount`'),SOURCE.replace('Grid()','CustomGrid()')]
  for source in variants:
   with self.subTest(source=source):self.assertIsNone(parse_background_source(source))
 def test_string_and_comment_decoys(self):
  base=SOURCE.replace('.backgroundColor(Color.White)','')
  self.assertIsNone(parse_background_source(base.replace("'Amount'","'.backgroundColor(Color.White)'")))
  self.assertIsNone(parse_background_source(base+'// backgroundColor(Color.White)\n'))
 def test_closed_request_no_observation_identity_or_negation_expansion(self):
  for query in [Q,'请定位负责层叠背景的 ArkTS 视图。','面板遮挡按钮，请定位负责层叠背景的 ArkTS 视图。']:
   self.assertEqual(parse_render_request(query).capability,'background');self.assertIsNone(recall_projection(query))
   self.assertEqual(recall_projection(query,allow_render_recall=True).terms,('backgroundcolor',))
  for query in [Q+' Also return other sources.',Q.replace('层叠背景','层叠和背景'),Q.replace('分类选择区遮挡金额输入控件','不要背景'),Q.replace('分类选择区遮挡金额输入控件','返回其它源码'),Q.replace('分类选择区遮挡金额输入控件','A.build'),Q.replace('分类选择区遮挡金额输入控件','不只背景'),Q.replace('分类选择区遮挡金额输入控件','勿选背景遮挡按钮'),Q.replace('分类选择区遮挡金额输入控件','需要任意源码')]:self.assertIsNone(parse_render_request(query),query)
