# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""New terminal presentation contract; synthetic candidate tests are not public reds."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.cache_scan_reading_source import parse_clock_scan
from tools.agent_memory_runtime.context_static_reading import static_reading_order,reading_request
from tools.agent_memory_runtime.storage import resolve_project,connect
from tools.agent_memory_runtime.context_budget import synchronize_estimate
from tools.agent_memory_runtime.performance_scoring import estimate_payload_tokens

PROTOCOL=Path(__file__).parents[1]/'docs/releases/static-reading-entry-20261118/retained-source-protocol.json'
SOURCE=json.loads(PROTOCOL.read_text())['sources']['src/WindowCache.ts']
QUERY='Locate executable eviction scan ownership.'

class ClockWitnessTests(unittest.TestCase):
    def test_retained_source_positive_and_renaming(self):
        self.assertEqual(parse_clock_scan(SOURCE)['method'],'store')
        self.assertIsNotNone(parse_clock_scan(SOURCE.replace('WindowCache','Ledger').replace('timestamp','age').replace('values','items')))

    def test_wrong_source_relationships_decline(self):
        variants=[
            SOURCE.replace('timestamp: Date.now()','payload: Date.now()'),
            SOURCE.replace('this.values.set','this.other.set'),
            SOURCE.replace('of this.values','of this.other'),
            SOURCE.replace('this.values.delete','this.other.delete'),
            SOURCE.replace('delete(selected)','delete(entryKey)'),
            SOURCE.replace('selected = entryKey','selected = token'),
            SOURCE.replace('entryValue.timestamp < minimum','entryValue.timestamp > minimum'),
            SOURCE.replace('minimum = entryValue.timestamp','minimum = 0'),
            SOURCE.replace('Date.now()','clock()'),
            SOURCE.replace('timestamp: number','timestamp: string'),
            SOURCE.replace('let selected:', 'notify(); let selected:'),
            SOURCE.replace('WindowCache','Date'),
            SOURCE+'export class Other {}',
            SOURCE.replace('this.values.delete(selected)','queueMicrotask(()=>{this.values.delete(selected)})'),
        ]
        for index,source in enumerate(variants):
            with self.subTest(index=index):self.assertIsNone(parse_clock_scan(source))

    def test_request_scope(self):
        for q in [QUERY,'Find the timestamp scan and delete implementation.','Return minimum-field scan and key deletion source.']:
            self.assertIsNotNone(reading_request(q))
        for q in ['Find FIFO eviction source.','Explain executable eviction scan ownership.',
                  'Locate "executable eviction scan ownership".',QUERY+' Also return logs.',
                  'Locate WindowCache.store.', 'Find the timestamp scan and delete implementation, not text.',
                  'A cache failure occurred. '+QUERY]:
            self.assertIsNone(reading_request(q))

class TerminalReadingTests(AgentMemoryTestBase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'project';self.root.mkdir()
        self.path=self.root/'src/WindowCache.ts';self.path.parent.mkdir();self.path.write_text(SOURCE)
        self.other=self.root/'src/OtherCache.ts';self.other.write_text(SOURCE.replace('WindowCache','OtherCache').replace('TimedValue','OtherValue'))
        self.run_memory(self.root,'learn-path','--path','src')
        self.project=resolve_project(str(self.root),str(self.memory_home(self.root)))
        with connect(self.project)as conn:
            self.rows=[dict(r)for r in conn.execute("SELECT * FROM code_symbols WHERE symbol='store'")]
        self.row=next(r for r in self.rows if r['file_path']=='src/WindowCache.ts')
        def candidate(row):
            return dict(file_path=row['file_path'],owner_name=row['owner_name'],owner_kind=row['owner_kind'],symbol=row['symbol'],score=8.5,evidence_score=8.5,reasons=['source_locatable'],source_range=dict(start_line=row['start_line'],end_line=row['end_line'],selection_reason='callable_symbol_range'))
        self.target=candidate(self.row);self.target2=candidate(next(r for r in self.rows if r!=self.row))
        self.old=dict(file_path='src/Inspector.ts',owner_name='Inspector',owner_kind='class',symbol='show',score=20.0,reasons=['exact_symbol'],source_range=dict(start_line=2,end_line=4,selection_reason='callable_symbol_range'))
        self.third=dict(self.old,file_path='src/Pool.ts',owner_name='Pool',symbol='remove')
        self.payload=dict(query=QUERY,source_freshness=dict(status='current',generation=self.row['index_generation']),query_handoff=dict(code_anchors=[self.anchor(self.row,SOURCE)],log_anchors=[{'preserved':'log evidence'}],path_context=dict(activated=False,path_candidates=[]),relation_hints=[{'relation':'imports','preserved':'real context'}],callable_evidence=dict(schema_version='agent-callable-evidence/v1',certainty='bounded',primary=self.old,alternatives=[self.target,self.third],boundary='retrieval_evidence_not_root_cause')),output_budget=dict(target_tokens=2000,estimated_tokens=0,truncated=False))
        synchronize_estimate(self.payload)

    def anchor(self,row,source):
        lo,hi=row['start_line'],row['end_line']
        return dict(file_path=row['file_path'],source_excerpts=[dict(start_line=lo,end_line=hi,content='\n'.join(source.splitlines()[lo-1:hi]),truncated=False)])

    def test_exact_permutation_preserves_all_other_evidence(self):
        before=deepcopy(self.payload);out=static_reading_order(self.project,self.payload)
        self.assertIsNot(out,self.payload);self.assertEqual(before,self.payload)
        evidence=out['query_handoff']['callable_evidence']
        new=[evidence['primary'],*evidence['alternatives']]
        old=[self.old,self.target,self.third]
        self.assertEqual([new[i]for i in evidence['reading_basis']['prior']],old)
        self.assertEqual(evidence['certainty'],'uncertain')
        restored=deepcopy(out);restored['query_handoff']['callable_evidence']=before['query_handoff']['callable_evidence'];restored['output_budget']=before['output_budget']
        self.assertEqual(restored,before)
        self.assertEqual(out['output_budget']['estimated_tokens'],estimate_payload_tokens(out))

    def test_absent_or_partial_target_noop(self):
        data=deepcopy(self.payload);data['query_handoff']['callable_evidence']['alternatives']=[self.third]
        self.assertIs(static_reading_order(self.project,data),data)
        data=deepcopy(self.payload);data['query_handoff']['code_anchors']=[]
        self.assertIs(static_reading_order(self.project,data),data)

    def test_stale_bytes_and_generation_noop(self):
        self.path.write_text(SOURCE+'\n')
        self.assertIs(static_reading_order(self.project,self.payload),self.payload)
        self.path.write_text(SOURCE);data=deepcopy(self.payload);data['source_freshness']['generation']+=1
        self.assertIs(static_reading_order(self.project,data),data)

    def test_multiple_proven_candidates_noop(self):
        data=deepcopy(self.payload);data['query_handoff']['callable_evidence']['alternatives']=[self.target,self.target2]
        row=next(r for r in self.rows if r!=self.row)
        data['query_handoff']['code_anchors'].append(self.anchor(row,self.other.read_text()))
        self.assertIs(static_reading_order(self.project,data),data)

    def test_second_source_proof_without_display_is_still_ambiguous(self):
        data=deepcopy(self.payload);data['query_handoff']['callable_evidence']['alternatives']=[self.target,self.target2]
        self.assertIs(static_reading_order(self.project,data),data)

    def test_budget_noop_no_trim(self):
        data=deepcopy(self.payload);data['output_budget']['target_tokens']=estimate_payload_tokens(data)
        synchronize_estimate(data);self.assertIs(static_reading_order(self.project,data),data)

    def test_only_authenticated_selected_windows_can_join(self):
        data=deepcopy(self.payload);span=data['query_handoff']['callable_evidence']['alternatives'][0]['source_range'];span.update(start_line=12,end_line=15,selection_reason='semantic_mechanism_window')
        self.assertIsNot(static_reading_order(self.project,data),data)
        span['start_line']=1;self.assertIs(static_reading_order(self.project,data),data)
        span.update(start_line=12,selection_reason='unknown');self.assertIs(static_reading_order(self.project,data),data)

    def test_activated_path_and_named_request_noop(self):
        data=deepcopy(self.payload);data['query_handoff']['path_context']['activated']=True
        self.assertIs(static_reading_order(self.project,data),data)
        data=deepcopy(self.payload);data['query']='Locate WindowCache.store.'
        self.assertIs(static_reading_order(self.project,data),data)

    def test_contradictory_owner_kind_and_duplicate_index_decline(self):
        data=deepcopy(self.payload);data['query_handoff']['callable_evidence']['alternatives'][0]['owner_kind']='component'
        self.assertIs(static_reading_order(self.project,data),data)
        with connect(self.project)as conn:
            conn.execute('UPDATE code_symbols SET qualified_name=? WHERE id=?',('Wrong.store',self.row['id']))
        self.assertIs(static_reading_order(self.project,self.payload),self.payload)

    def test_terminal_handler_does_not_feed_new_primary_to_compaction(self):
        from types import SimpleNamespace
        from tools.agent_memory_runtime import command_handlers as handlers
        events=[];raw={'raw':True};ordered={'ordered':True}
        args=SimpleNamespace(project=str(self.root),memory_home=str(self.memory_home(self.root)),query=QUERY,compact=True,json=True)
        facade=SimpleNamespace(execute=lambda *a:raw)
        def compact(data):
            self.assertIs(data,raw);events.append('compact');return self.payload
        def reorder(project,data):
            self.assertEqual(events,['compact']);self.assertIs(data,self.payload);events.append('reading');return ordered
        with patch.object(handlers,'build_context_facade',return_value=facade),patch.object(handlers,'compact_context',side_effect=compact), \
             patch('tools.agent_memory_runtime.context_static_reading.static_reading_order',side_effect=reorder), \
             patch.object(handlers,'record_query_usage'),patch.object(handlers,'redact_source_excerpt_bodies',side_effect=lambda x:x), \
             patch.object(handlers,'append_query_performance_sample'),patch.object(handlers,'output')as output:
            handlers.context(args);output.assert_called_once_with(ordered,True)
        self.assertEqual(events,['compact','reading'])

    def test_raw_cli_never_calls_reading_migration(self):
        from types import SimpleNamespace
        from tools.agent_memory_runtime import command_handlers as handlers
        raw={'raw':True};args=SimpleNamespace(project=str(self.root),memory_home=str(self.memory_home(self.root)),query=QUERY,compact=False,json=True)
        with patch.object(handlers,'build_context_facade',return_value=SimpleNamespace(execute=lambda *a:raw)), \
             patch.object(handlers,'compact_context')as compact, \
             patch('tools.agent_memory_runtime.context_static_reading.static_reading_order')as migration, \
             patch.object(handlers,'record_query_usage'),patch.object(handlers,'redact_source_excerpt_bodies',side_effect=lambda x:x), \
             patch.object(handlers,'append_query_performance_sample'),patch.object(handlers,'output')as output:
            handlers.context(args);output.assert_called_once_with(raw,True)
            compact.assert_not_called();migration.assert_not_called()
