# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Finite caller-local qualification; temporary development inputs, not an AFTER."""
import json
import tempfile
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.query_caller_ownership import (
    plural_caller_member, collect_bounded_caller_owners, requested_caller_identities,
    ResolvedCallerItem,
)
from tools.agent_memory_runtime.query_code_selection import diverse_code_matches
from tools.agent_memory_runtime.storage import resolve_project, connect

Q = 'Find actual callers of ModalBridge.finish.'
P = Path(__file__).resolve().parents[1] / 'docs/eval/indirect-caller-current/protocol.json'

class FinitePluralCallerTests(AgentMemoryTestBase):
    def test_exact_grammar_and_refusals(self):
        for q in (Q, ' Find the actual callers of ModalBridge.finish ', Q.lower()):
            self.assertEqual(q.split('of ')[1].strip(' .'), plural_caller_member(q))
        for q in ('"'+Q+'"', Q.replace('ModalBridge.finish','`ModalBridge.finish`'),
                  Q.replace('callers','caller'), Q.replace('actual','only actual'),
                  Q.replace('actual','single actual'), 'Do not '+Q, Q+' Explain it.',
                  Q.replace('finish.','finish and ModalBridge.reset.'),
                  Q.replace('of','for'), Q.replace('.finish',''),
                  Q.replace('.finish','.nested.finish'), Q.replace('Find','Compare'),
                  Q.replace('Find','Find one'), Q+' except ReviewPanel.',
                  Q.replace('Find','Find no')):
            with self.subTest(q=q): self.assertIsNone(plural_caller_member(q))

    def test_real_unique_member_binding_and_projection_controls(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            sources = json.loads(P.read_text())['sources']
            sources['ReviewPanel.ets'] = sources['ConfirmPanel.ets'].replace('ConfirmPanel','ReviewPanel')
            for name, source in sources.items(): (root/name).write_text(source)
            self.run_memory(root, 'init')
            self.run_memory(root, 'learn-path', '--path', '.')
            project = resolve_project(str(root), str(self.memory_home(root)))
            seed = [{'file_path':'ModalBridge.ets', 'score':20}]
            rows = collect_bounded_caller_owners(project, seed, Q)
            self.assertEqual({'ConfirmPanel.ets','ReviewPanel.ets'}, {r['file_path'] for r in rows})
            self.assertTrue(all(isinstance(r,ResolvedCallerItem) for r in rows))
            qualified = requested_caller_identities(rows,Q)
            self.assertIsNotNone(qualified)
            self.assertEqual(rows, diverse_code_matches(rows,5,query=Q))
            self.assertEqual(rows[:1], diverse_code_matches(rows,1,query=Q))
            for projected in ([dict(r) for r in rows], json.loads(json.dumps(rows))):
                self.assertIsNone(requested_caller_identities(projected,Q))
            self.assertIsNone(requested_caller_identities(rows,Q+' More.'))
            forged = [dict(r, request_binding=r.request_binding) for r in rows]
            self.assertIsNone(requested_caller_identities(forged,Q))
            broken = [ResolvedCallerItem(dict(r),Q,(999,)) for r in rows]
            broken[1]['source_digest'] = 'b'*64
            self.assertIsNone(requested_caller_identities(broken,Q))
            # A same-shaped file target must not receive member qualification.
            file_rows = collect_bounded_caller_owners(project,seed,'Find actual callers of ModalBridge.ets.')
            self.assertTrue(file_rows)
            self.assertTrue(all(not isinstance(r,ResolvedCallerItem) for r in file_rows))
            # Duplicate owner/member outside the seed invalidates project uniqueness.
            with connect(project) as conn:
                conn.execute("UPDATE code_symbols SET owner_name='ModalBridge',symbol='finish' WHERE project_id=? AND file_path='ResetPanel.ets' AND symbol='onClick'",(project.project_id,))
                conn.commit()
            self.assertEqual([],collect_bounded_caller_owners(project,seed,Q))
