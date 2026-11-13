# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.callable_behavior_hints import event_collection_hints

EVIDENCE=Path(__file__).resolve().parents[1]/'docs/evidence/async-ordering'
PROTOCOL=json.loads((EVIDENCE/'protocol.json').read_text())


class AsyncOrderingOwnerTests(AgentMemoryTestBase):
    def check_public(self, index, suffix='.ets'):
        with tempfile.TemporaryDirectory() as directory:
            project=Path(directory)
            for path,source in PROTOCOL['sources'].items():
                (project/Path(path).with_suffix(suffix)).write_text(source)
            self.run_memory(project,'init')
            self.run_memory(project,'learn-path','--path','.')
            case=PROTOCOL['queries'][index]
            data=json.loads(self.run_memory(project,'context','--query',case['query'],'--compact','--json').stdout)
            anchors=data['query_handoff']['code_anchors']
            paths={Path(a['file_path']).stem for a in anchors}
            self.assertIn(Path(case['required']).stem,paths)
            self.assertFalse({Path(p).stem for p in case['excluded']} & paths)
            if index==1:
                excerpts=[e for a in anchors for e in a.get('source_excerpts',[])]
                lines={n for e in excerpts for n in range(e['start_line'],e['end_line']+1)}
                self.assertTrue(set(range(4,12))<=lines)

    def test_chinese_owner_and_explicit_writer(self):
        for suffix in ('.ts','.ets'):
            for index in (1,2):
                with self.subTest(suffix=suffix,index=index):self.check_public(index,suffix)

    @unittest.expectedFailure
    def test_preserved_english_owner_failure(self):
        self.check_public(0)

    def test_bounded_marker_controls(self):
        entity=SimpleNamespace(name='select',file_path='Reader.ets')
        good='async select(k: number) { await read(); if (k !== this.pending) { return } this.text = value }'
        self.assertIn('orderingguard',event_collection_hints(entity,good))
        controls=[
            'select(k: number) { if (k !== this.pending) { return } }',
            'async select(k: number) { await read(); this.text = value }',
            'async select(k: number) { await read(); // if (k !== this.pending)\n }',
            'async select(k: number) { const text="if (k !== this.pending)"; await read(); }',
            'async select(k: number) { await read(); (() => { if(k !== this.pending) return })() }',
            'async select(k: number) { await read(); const re=/if (k !== this.pending)/; }',
        ]
        for source in controls:
            self.assertNotIn('orderingguard',event_collection_hints(entity,source))
        self.assertNotIn('orderingguard',event_collection_hints(SimpleNamespace(name='select',file_path='Reader.py'),good))
