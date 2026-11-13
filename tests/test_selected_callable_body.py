# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json
import tempfile
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase

EVIDENCE = Path(__file__).resolve().parents[1] / 'docs/evidence/callable-body-rebuild'


class SelectedCallableBodyTests(AgentMemoryTestBase):
    def test_public_target_body_and_existing_lines(self):
        source = (EVIDENCE / 'source.ts').read_text()
        queries = json.loads((EVIDENCE / 'queries.json').read_text())
        baseline = json.loads((EVIDENCE / 'baseline.json').read_text())
        outputs = []
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / 'fixture'
            project.mkdir()
            (project / 'CapabilityReader.ts').write_text(source)
            self.run_memory(project, 'init')
            self.run_memory(project, 'learn-path', '--path', 'CapabilityReader.ts', '--json')
            for query, old in zip(queries, baseline):
                result = json.loads(self.run_memory(project, 'context', '--query', query, '--compact', '--json').stdout)
                outputs.append({'query':query, 'data':result})
                before = old['data']['query_handoff']
                handoff = result['query_handoff']
                with self.subTest(query=query):
                    self.assertEqual(before['callable_evidence'], handoff['callable_evidence'])
                    expected = range(4, 8) if '.label' not in query else range(11,14)
                    excerpts = [e for a in handoff['code_anchors'] for e in a.get('source_excerpts', [])]
                    lines = {n for e in excerpts for n in range(e['start_line'], e['end_line']+1)}
                    self.assertTrue(set(expected) <= lines, excerpts)
                    for anchor in before['code_anchors']:
                        for excerpt in anchor.get('source_excerpts', []):
                            self.assertTrue(set(range(excerpt['start_line'],excerpt['end_line']+1)) <= lines)
                    for excerpt in excerpts:
                        actual = '\n'.join(source.splitlines()[excerpt['start_line']-1:excerpt['end_line']])
                        self.assertEqual(actual, excerpt['content'])
        (EVIDENCE / 'latest.json').write_text(json.dumps(outputs,ensure_ascii=False,indent=2))

    def test_tail_guard_counterexamples(self):
        from tools.agent_memory_runtime.context_callable_excerpt import retain_callable_tail
        lines = (EVIDENCE / 'source.ts').read_text().splitlines(True)
        path = Path('CapabilityReader.ts')
        original = {'symbol':'label', 'start_line':11, 'end_line':13}
        focused = {'start_line':1, 'end_line':11}
        self.assertEqual(13, retain_callable_tail(path, original, focused, lines, 0, 40)['end_line'])
        controls = [
            (Path('CapabilityReader.java'), original, focused, 0, 40),
            (path, {**original,'symbol':'resolve'}, focused, 0, 40),
            (path, {**original,'end_line':14}, focused, 0, 40),
            (path, original, {'start_line':12,'end_line':12}, 0, 40),
            (path, original, {'start_line':1,'end_line':14}, 0, 40),
            (path, original, focused, 3, 40),
            (path, original, focused, 0, 10),
        ]
        for p, old, window, offset, limit in controls:
            with self.subTest(old=old,window=window,offset=offset,limit=limit):
                self.assertEqual(window, retain_callable_tail(p, old, window, lines, offset, limit))
