# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import copy
import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.context_source_excerpt import read_excerpt
from tools.agent_memory_runtime.source_line_window import read_source_interval
from tools.agent_memory_runtime.context_source_recovery import recover_partial_primary, RANK_REASONS

DATA = Path(__file__).resolve().parents[1] / 'docs/eval/partial-source-rank-trade-20261114'
PROTOCOL = json.loads((DATA / 'protocol.json').read_text())
RAW = json.loads((DATA / 'public-before.json').read_text())[0]['payload']
BASE = json.loads((DATA / 'public-before.json').read_text())[1]['payload']

class PartialSourceRankTradeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name, source in PROTOCOL['sources'].items():
            (self.root / name).write_text(source)
        self.payload = copy.deepcopy(BASE)

    def test_transaction_restores_source_preserving_every_other_fact(self):
        before = copy.deepcopy(self.payload)
        result = recover_partial_primary(self.payload, str(self.root), 1500, source_rows=RAW['wiki_matches'])
        self.assertIsNot(result, self.payload)
        self.assertEqual(before, self.payload)
        expected = copy.deepcopy(before)
        evidence = expected['query_handoff']['callable_evidence']
        for row in [evidence['primary'], *evidence['alternatives']]:
            row.pop('score', None); row.pop('evidence_score', None)
            row['reasons'] = [x for x in row['reasons'] if x not in RANK_REASONS]
        for payload in (result, expected):
            payload['query_handoff']['code_anchors'][0].pop('source_excerpts')
            payload['query_handoff']['source_excerpt_policy'].pop('excerpt_chars')
            payload.pop('output_budget')
        self.assertEqual(expected, result)

    def test_unknown_mechanism_identity_reasons_and_certificates_survive(self):
        evidence = self.payload['query_handoff']['callable_evidence']
        row = evidence['primary']
        row['reasons'] += ['semantic_mechanism', 'source_operation', 'unknown_future_reason']
        row['certificate'] = {'id': 'x', 'digest': 'abc', 'uncertainty': ['unresolved']}
        result = recover_partial_primary(self.payload, str(self.root), 2500, source_rows=RAW['wiki_matches'])
        actual = result['query_handoff']['callable_evidence']['primary']
        self.assertEqual(row['certificate'], actual['certificate'])
        self.assertTrue(set(row['reasons']) - RANK_REASONS <= set(actual['reasons']))
        self.assertEqual(row['callable_roles'], actual['callable_roles'])
        self.assertEqual(len(evidence['alternatives']),len(result['query_handoff']['callable_evidence']['alternatives']))

    def test_over_budget_and_explicit_source_caps_roll_back(self):
        for kwargs in ({'token_budget':100}, {'token_budget':1500,'source_char_cap':100},
                       {'token_budget':1500,'source_line_cap':5}, {'token_budget':1500,'total_char_cap':100}):
            self.assertIs(self.payload, recover_partial_primary(self.payload,str(self.root),source_rows=RAW['wiki_matches'],**kwargs))
        value=copy.deepcopy(self.payload)
        rows=copy.deepcopy(RAW['wiki_matches'])
        path=self.root/'RefreshStore.ets'
        text=path.read_text().replace('  private adapter:', '  private extraConfigurationValue: number = 0\n  private adapter:')
        path.write_text(text)
        value['query_handoff']['code_anchors'][0]['source_ranges'][0]['end_line'] += 1
        for row in rows:
            if row['file_path']=='RefreshStore.ets':
                row['end_line'] += 1
                row['source_digest']=hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertIs(value,recover_partial_primary(value,str(self.root),1500,source_rows=rows))
        self.assertIsNot(value,recover_partial_primary(value,str(self.root),2500,source_rows=rows))

    def test_digest_binding_tail_mutation_missing_and_escape(self):
        rows=RAW['wiki_matches']
        path=self.root/'RefreshStore.ets'
        original=path.read_bytes()
        path.write_bytes(original.replace(b'loadCurrent()',b'loadChanged()'))
        self.assertIs(self.payload,recover_partial_primary(self.payload,str(self.root),2500,source_rows=rows))
        path.unlink()
        self.assertIs(self.payload,recover_partial_primary(self.payload,str(self.root),2500,source_rows=rows))
        path.write_bytes(original)
        self.assertIs(self.payload,recover_partial_primary(self.payload,str(self.root),2500))
        escaped=copy.deepcopy(self.payload)
        escaped['query_handoff']['code_anchors'][0]['file_path']='../RefreshStore.ets'
        self.assertIs(escaped,recover_partial_primary(escaped,str(self.root),2500,source_rows=rows))
        bad=copy.deepcopy(self.payload)
        bad['query_handoff']['code_anchors'][0]['source_excerpts'][0]['start_line']=True
        self.assertIs(bad,recover_partial_primary(bad,str(self.root),2500,source_rows=rows))

    def test_byte_fidelity_and_typed_raw_identity_binding(self):
        path=self.root/'RefreshStore.ets'
        original=path.read_bytes()
        for raw in (original.replace(b'\n',b'\r\n'), original.replace(b'\n',b'\r'),
                    original.replace(b"result: string = ''",b"result: string = '\xff'"),
                    original.replace(b"result: string = ''","result: string = '\u2028'".encode())):
            path.write_bytes(raw)
            value=copy.deepcopy(self.payload);rows=copy.deepcopy(RAW['wiki_matches'])
            for row in rows:
                if row['file_path']=='RefreshStore.ets':row['source_digest']=hashlib.sha256(raw).hexdigest()
            anchor=value['query_handoff']['code_anchors'][0]
            anchor['source_excerpts'][0]=read_excerpt(path,anchor['source_ranges'][0],750)
            out=recover_partial_primary(value,str(self.root),2500,source_rows=rows)
            self.assertIsNot(out,value)
            # The shared reader retains line-ending characters; normalize them as read_excerpt does.
            expected='\n'.join(line.rstrip('\r\n') for line in read_source_interval(path,1,32,40).lines)
            self.assertEqual(expected,out['query_handoff']['code_anchors'][0]['source_excerpts'][0]['content'])
        path.write_bytes(original)
        for key,bad in [('id',-1),('kind','symbol'),('file_path','elsewhere.ets'),
                        ('symbol','other'),('start_line',True),('end_line',99)]:
            rows=copy.deepcopy(RAW['wiki_matches']);rows[0][key]=bad
            self.assertIs(self.payload,recover_partial_primary(self.payload,str(self.root),2500,source_rows=rows),key)

    def test_multiple_owners_stale_and_unproven_source_preserve_original(self):
        for change in ('multi','stale','no_range','no_excerpt','mismatch','complete','unknown_reason'):
            value=copy.deepcopy(self.payload);a=value['query_handoff']['code_anchors'][0]
            if change=='multi':value['query_handoff']['code_anchors'].append(copy.deepcopy(a))
            elif change=='stale':value['source_freshness']['status']='stale'
            elif change=='no_range':a['source_ranges']=[]
            elif change=='no_excerpt':a['source_excerpts']=[]
            elif change=='mismatch':a['source_excerpts'][0]['content']='not current source'
            elif change=='complete':a['source_excerpts'][0]['truncated']=False
            else:
                for row in [value['query_handoff']['callable_evidence']['primary'],*value['query_handoff']['callable_evidence']['alternatives']]:
                    row.pop('score',None);row.pop('evidence_score',None);row['reasons']=['unknown']
            self.assertIs(value,recover_partial_primary(value,str(self.root),1500,source_rows=RAW['wiki_matches']),change)

class PartialSourcePublicTests(AgentMemoryTestBase):
    def test_actual_cli_restores_behavior_without_removing_logs_or_owners(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name,source in PROTOCOL['sources'].items():(root/name).write_text(source)
            self.run_memory(root,'init');self.run_memory(root,'learn-path','--path','.')
            out=json.loads(self.run_memory(root,'context','--query',PROTOCOL['queries'][0],'--compact','--json').stdout)
            excerpt=out['query_handoff']['code_anchors'][0]['source_excerpts'][0]
            self.assertFalse(excerpt['truncated'])
            self.assertIn('await this.adapter.loadCurrent()',excerpt['content'])
            self.assertLessEqual(out['output_budget']['estimated_tokens'],1500)
            self.assertEqual(BASE['query_handoff']['log_anchors'],out['query_handoff']['log_anchors'])
            self.assertEqual(BASE['query_handoff']['path_context'],out['query_handoff']['path_context'])
