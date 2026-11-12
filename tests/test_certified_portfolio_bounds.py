# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
from __future__ import annotations
import copy
import unittest
from tools.agent_memory_runtime.query_certified_portfolio_bounds import MARKER, certify_selected_bounds, certified_projection
from tools.agent_memory_runtime.query_callable_passage_portfolio import build_callable_passage_portfolio
from tools.agent_memory_runtime.context_callable_focus import focus_callable_anchors


def fixture():
    path = 'src/Transaction.ets'
    candidates = [dict(file_path=path, symbol=s, owner_name='Transaction', start_line=a, end_line=b,
                       reasons=['exact_symbol', 'salient_query_evidence', 'multi_term_method_evidence'])
                  for s,a,b in [('commitCheckpoint',9,21),('rollbackCheckpoint',23,25)]]
    ranges = [dict(file_path=path, symbol=c['symbol'], start_line=a, end_line=b,
                   callable_start_line=c['start_line'], callable_end_line=c['end_line'],
                   selection_reason=reason, mechanism_kind='persistence_write')
              for c,a,b,reason in [(candidates[0],13,17,'semantic_mechanism_window'),
                                   (candidates[1],23,25,'callable_symbol_range')]]
    members = [dict(file_path=path, symbol=c['symbol'], owner_name='Transaction',
                    source_range={k:r[k] for k in ['start_line','end_line','selection_reason','mechanism_kind']})
               for c,r in zip(candidates,ranges)]
    anchors = [dict(file_path=path,symbol='commitCheckpoint',start_line=9,end_line=21,
                    record_id=409,summary='commit summary',source='wiki',symbol_type='function')]
    return members,copy.deepcopy(members[0]),candidates,ranges,anchors


def portfolio(members):
    return dict(state='composed',target_scope='multiple',selection_basis=[MARKER],members=members)


def project(m,p,a):
    return focus_callable_anchors(a,dict(certainty='bounded',primary=p,passage_portfolio=portfolio(m)),False)


def invalid_controls():
    rows={}
    def add(name,change):
        row=fixture();change(*row);rows[name]=row
    add('single',lambda m,p,c,r,a:m.pop())
    add('empty_owner',lambda m,p,c,r,a:p.update(owner_name=''))
    add('other_owner',lambda m,p,c,r,a:m[1].update(owner_name='Other'))
    add('primary_absent',lambda m,p,c,r,a:p.update(symbol='absent'))
    add('other_file',lambda m,p,c,r,a:p.update(file_path='other'))
    add('missing_bounds',lambda m,p,c,r,a:r[1].pop('callable_start_line'))
    for v in [False,0,-1,30,'9']:
        add('invalid_raw_'+str(v),lambda m,p,c,r,a,v=v:r[0].update(callable_start_line=v))
        add('invalid_candidate_'+str(v),lambda m,p,c,r,a,v=v:c[0].update(start_line=v))
    for start,end in [(8,17),(13,22),(False,17),(17,13)]:
        def change(m,p,c,r,a,start=start,end=end):
            r[0].update(start_line=start,end_line=end);m[0]['source_range'].update(start_line=start,end_line=end)
        add('window_'+str((start,end)),change)
    add('candidate_disagrees',lambda m,p,c,r,a:c[0].update(end_line=22))
    for k,v in [('owner_name','Other'),('start_line',8),('end_line',22)]:
        add('candidate_conflict_'+k,lambda m,p,c,r,a,k=k,v=v:c.append({**c[0],k:v}))
    for k,v in [('start_line',12),('end_line',18),('callable_end_line',22)]:
        add('raw_conflict_'+k,lambda m,p,c,r,a,k=k,v=v:r.append({**r[0],k:v}))
    add('over_cap',lambda m,p,c,r,a:m.extend(copy.deepcopy(m)))
    return rows


class CertifiedPortfolioBoundsTests(unittest.TestCase):
    def test_positive_and_metadata(self):
        m,p,c,r,a=fixture();before=copy.deepcopy((m,p,c,r,a));out=certify_selected_bounds(m,p,c,r)
        self.assertEqual(before,(m,p,c,r,a));self.assertTrue(certified_projection(portfolio(out),p))
        self.assertEqual((13,17),(out[0]['source_range']['start_line'],out[0]['source_range']['end_line']))
        for old,new in zip(m,out):
            self.assertEqual(old,{**new,'source_range':{k:v for k,v in new['source_range'].items() if not k.startswith('callable_')}})
        result=project(out,p,a)
        self.assertEqual([(9,21),(23,25)],[(x['start_line'],x['end_line']) for x in result])
        self.assertEqual(409,result[0]['record_id']);self.assertNotIn('record_id',result[1]);self.assertNotIn('summary',result[1])

    def test_actual_builder_and_uncertified_fallback(self):
        m,p,c,r,a=fixture()
        build=lambda:build_callable_passage_portfolio('Inspect both commitCheckpoint and rollbackCheckpoint.',dict(callable_candidates=c,source_ranges=r),dict(primary=p))
        out=build();self.assertIn(MARKER,out['selection_basis']);self.assertFalse(out['candidate_recall_changed'])
        self.assertEqual([x['symbol'] for x in m],[x['symbol'] for x in out['members']])
        r[0].pop('callable_end_line');out=build();self.assertNotIn(MARKER,out['selection_basis'])
        self.assertEqual((13,17),(out['members'][0]['source_range']['start_line'],out['members'][0]['source_range']['end_line']))

    def test_all_invalid_producer_inputs_atomically_fall_back(self):
        for name,(m,p,c,r,a) in invalid_controls().items():
            with self.subTest(name=name):self.assertIsNone(certify_selected_bounds(m,p,c,r))

    def test_identical_duplicates_and_already_full_span(self):
        m,p,c,r,a=fixture();expected=certify_selected_bounds(m,p,c,r)
        c.append(copy.deepcopy(c[0]));r.append(copy.deepcopy(r[0]));self.assertEqual(expected,certify_selected_bounds(m,p,c,r))
        m,p,c,r,a=fixture();r[0].update(start_line=9,end_line=21);m[0]['source_range'].update(start_line=9,end_line=21);p['source_range'].update(start_line=9,end_line=21)
        self.assertEqual(9,certify_selected_bounds(m,p,c,r)[0]['source_range']['callable_start_line'])

    def test_vetoes_unchanged(self):
        m,p,c,r,a=fixture();e=dict(certainty='bounded',primary=p,passage_portfolio=portfolio(certify_selected_bounds(m,p,c,r)))
        for mode in ['exclusive','activated','log','graph','uncertain']:
            aa,ee=copy.deepcopy((a,e));path=False
            if mode=='exclusive':path=True
            if mode=='activated':path={'activated':True}
            if mode=='log':aa[0]['log_identity_match']=True
            if mode=='graph':aa[0]['graph_neighbor']=True
            if mode=='uncertain':ee['certainty']='uncertain'
            self.assertEqual(aa,focus_callable_anchors(aa,ee,path))

    def test_invalid_markers_do_not_authorize_expansion(self):
        m,p,c,r,a=fixture()
        for tweak in ['missing','false','untyped','bad_scope','bad_range','duplicate','inactive','crossfile']:
            d=portfolio(certify_selected_bounds(m,p,c,r))
            if tweak=='missing':d['selection_basis']=[]
            if tweak=='false':d['selection_basis']=[False]
            if tweak=='untyped':d['members'][1]['source_range'].pop('callable_end_line')
            if tweak=='bad_scope':d['target_scope']='single'
            if tweak=='bad_range':d['members'][1]['source_range']['callable_end_line']=True
            if tweak=='duplicate':d['members'].append(copy.deepcopy(d['members'][0]))
            if tweak=='inactive':d['state']='inactive'
            if tweak=='crossfile':d['selection_basis'].append('explicit_cross_file_targets')
            self.assertFalse(certified_projection(d,p))
            e=dict(certainty='bounded',primary=p,passage_portfolio=d);old=copy.deepcopy(e)
            old['passage_portfolio']['selection_basis']=[v for v in d['selection_basis'] if v!=MARKER]
            self.assertEqual(focus_callable_anchors(a,old,False),focus_callable_anchors(a,e,False))

    def test_metadata_requires_exact_path_symbol_and_fullrange(self):
        for field,value in [('symbol','other'),('file_path','other'),('start_line',8),('end_line',22)]:
            m,p,c,r,a=fixture();a[0][field]=value
            self.assertTrue(all('record_id' not in x for x in project(certify_selected_bounds(m,p,c,r),p,a)))
        m,p,c,r,a=fixture();a.append(dict(file_path=p['file_path'],symbol=m[1]['symbol'],start_line=23,end_line=25,record_id=410))
        self.assertEqual([409,410],[x['record_id'] for x in project(certify_selected_bounds(m,p,c,r),p,a)])
