# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json
from pathlib import Path
import unittest
from tools.agent_memory_runtime.query_render_recall import parse_render_request, recall_projection, RenderRecall, request_terms

D = Path(__file__).parents[1] / 'docs/evidence/render05-zh-request'
P = json.loads((D/'protocol.json').read_text())

class ChineseRenderRequestTests(unittest.TestCase):
    def test_frozen_requests(self):
        for case in P['queries']:
            with self.subTest(case=case['id']):
                r=parse_render_request(case['query'])
                self.assertEqual(r is not None,case['semantic_cleanup_request'] and '不要返回' not in case['query'])
                if r:
                    self.assertEqual(r.capability,'cleanup')
                    self.assertEqual(request_terms(r),('column','row','text'))

    def test_frozen_negatives_and_enforced_positive_owner_exclusion(self):
        for q in P['negative_request_controls']:
            with self.subTest(query=q):
                r=parse_render_request(q)
                self.assertIsNone(r)

    def test_all_exclusions_fall_back(self):
        base='请定位清洗并渲染正文的 view，不要返回 {} 数据类。'
        for name in ('X','Record','消息','MessageRecord 或 OtherRecord','messageRecord','Message_Record',
                     'MessageRecord','MessageRecordPreview','ArticleRecord'):
            self.assertIsNone(parse_render_request(base.format(name)))

    def test_domain_rename_and_observation_not_identity(self):
        for topic in ('文章详情','消息详情','收据详情','通知详情','评论详情'):
            q=f'{topic}仍显示 HTML 标签，请查找负责清洗并渲染正文的 view。'
            r=parse_render_request(q);self.assertIsNotNone(r)
            projection=recall_projection(q,allow_render_recall=True)
            self.assertIsInstance(projection,RenderRecall)
            self.assertEqual(projection.terms,('column','row','text'))
        for prefix in ('请返回消息','不要消息','消息和正文','引用消息','日志消息',
                       '忽略消息','另查消息','同时检查消息','未知详情','消息详情和收据详情'):
            self.assertIsNone(parse_render_request(prefix+'仍显示 HTML 标签，请定位清洗并渲染正文的 view。'))

    def test_conjunction_and_request_scope(self):
        good='请定位清洗并渲染正文的 view。'
        for q in (good.replace('并','或'),good.replace('清洗','不清洗'),good.replace('清洗并','仅'),
                  good.replace('请定位','请解释'), '“'+good+'”', '日志内容：'+good,
                  good+'同时返回数据类。',good.replace('view','view和数据类')):
            self.assertIsNone(parse_render_request(q))

class ChineseRenderTransportTests(unittest.TestCase):
    def use_fixture(self, query, operation):
        import test_render_selection as fixture_module
        from unittest.mock import patch
        fixture=fixture_module.RenderSelectionTests();fixture.setUp()
        fixture.baseline['query']=query;fixture.trial['query']=query
        try:
            with patch.object(fixture_module,'Q',query):
                operation(fixture)
        finally:
            fixture.tearDown()

    def test_chinese_two_sources_and_complete_snapshot(self):
        from tools.agent_memory_runtime.context_compact import compact_context
        def check(f):
            f.clone_owner('SecondView')
            out=compact_context(f.bind())
            self.assertEqual({a['file_path']for a in out['query_handoff']['code_anchors']},{'MessageSurface.ets','SecondView.ets'})
            self.assertTrue(all(len(a.get('source_excerpts',[]))==2 and all(not e['truncated']for e in a['source_excerpts'])for a in out['query_handoff']['code_anchors']))
            self.assertLessEqual(out['output_budget']['estimated_tokens'],1500)
        self.use_fixture('请定位清洗并渲染文本的视图源码。',check)

    def test_chinese_protected_log_and_path_unchanged(self):
        def check(f):
            f.baseline['query_handoff']['log_anchors']=[{'message_template':'retained log'}]
            self.assertIs(f.bind(),f.baseline)
            f.baseline['query_handoff']['log_anchors']=[]
            f.trial['query_handoff']['path_context']={'activated':True}
            self.assertIs(f.bind(),f.baseline)
        self.use_fixture('请返回负责清洗并渲染正文的 UI 源码。',check)

    def test_chinese_excluding_actual_positive_owner_falls_back(self):
        self.use_fixture('请定位清洗并渲染正文的 view，不要返回 MessageSurface 数据类。',lambda f:self.assertIs(f.bind(),f.baseline))

    def test_chinese_stale_source_identity_falls_back(self):
        def check(f):
            f.db.execute("UPDATE code_symbols SET source_digest='bad' WHERE symbol='plainBody'")
            self.assertIs(f.bind(),f.baseline)
        self.use_fixture('请定位清洗并渲染文本的视图源码。',check)

if __name__=='__main__':unittest.main()
