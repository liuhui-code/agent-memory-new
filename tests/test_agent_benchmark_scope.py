"""Independent development contract checks; no original evaluation replay."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_agent_benchmark import benchmark_pack, observation
from tools.agent_memory_runtime.agent_benchmark import run_cases, select_cases
from tools.agent_memory_runtime.agent_benchmark_cases import validate_case_pack
from tools.agent_memory_runtime.agent_benchmark_eval import evaluate_agent_benchmark, score_observation
from tools.agent_memory_runtime.agent_benchmark_protocol import run_benchmark_agent
from tools.agent_memory_runtime.agent_benchmark_scope import require_diagnosis_cases
from examples.codex_benchmark_prompt import build_prompt
from examples.ollama_benchmark_runner import run_request

ROOT=Path(__file__).resolve().parents[1]

class BenchmarkScopeTests(unittest.TestCase):
    def setUp(self):
        self.diagnosis=benchmark_pack(Path('/unused'))['cases'][0]
        self.design=copy.deepcopy(self.diagnosis)
        self.design.update(id='design-cache-policy',task_type='design',provenance={'kind':'independent_development_fixture'})
        self.design['task']={'description':'Compare cache replacement strategies and their tradeoffs; no incident is alleged.'}
        self.obs=observation('case-1','memory','route',['src/Profile.ets'],50)

    def test_design_case_loading_still_supported(self):
        p=benchmark_pack(Path('/unused'));p['cases']=[self.design]
        self.assertEqual(validate_case_pack(p)['cases'][0]['task_type'],'design')

    def test_selected_diagnosis_from_mixed_pack_is_allowed(self):
        require_diagnosis_cases(select_cases([self.diagnosis,self.design],['case-1']))
        for cases in ([self.design],[self.diagnosis,self.design]):
            with self.assertRaisesRegex(SystemExit,'design-cache-policy'):
                require_diagnosis_cases(cases)

    def test_diagnosis_scores_unchanged_and_legacy_missing_type_supported(self):
        before=json.loads((ROOT/'docs/releases/design-benchmark-scope-20261118/diagnosis-before.json').read_text())
        self.assertEqual(score_observation(self.diagnosis,self.obs),before['score'])
        self.assertEqual(build_prompt({'case':self.diagnosis}),before['prompt'])
        legacy=copy.deepcopy(self.diagnosis);del legacy['task_type']
        self.assertEqual(score_observation(legacy,self.obs),before['score'])
        for value in (None,'source_reading',''):
            with self.assertRaises(SystemExit):require_diagnosis_cases([{'task_type':value}])

    def test_design_cannot_be_scored_or_prompted(self):
        for call in (lambda:score_observation(self.design,self.obs),lambda:evaluate_agent_benchmark({},[self.design],[]),lambda:build_prompt({'case':self.design})):
            with self.assertRaisesRegex(SystemExit,'diagnosis execution/scoring only'):call()

    def test_mixed_batch_rejects_before_first_runner(self):
        with patch('tools.agent_memory_runtime.agent_benchmark.run_benchmark_agent') as run:
            with self.assertRaises(SystemExit):run_cases(Path('/unused'),[self.diagnosis,self.design],'unused',5,False)
            run.assert_not_called()

    def test_direct_run_rejects_before_resolver_or_workspace(self):
        with patch('tools.agent_memory_runtime.agent_benchmark_protocol.resolve_runner') as resolve:
            with self.assertRaises(SystemExit):run_benchmark_agent(Path('/unused'),self.design,'memory','unused',5)
            resolve.assert_not_called()

    def test_direct_external_runners_reject_before_work(self):
        with patch('examples.ollama_benchmark_runner.load_memory_context') as query:
            with self.assertRaisesRegex(SystemExit,'diagnosis execution/scoring only'):
                run_request({'case':self.design},host='http://127.0.0.1:1',model='unused',timeout=1)
            query.assert_not_called()
        p=subprocess.run([sys.executable,str(ROOT/'examples/codex-agent-benchmark-runner.py')],input=json.dumps({'case':self.design}),text=True,capture_output=True)
        self.assertNotEqual(p.returncode,0);self.assertIn('diagnosis execution/scoring only',p.stderr)
        self.assertNotIn('workspace',p.stderr)

    def test_actual_cli_refuses_design_before_ledger_and_runner(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);project=root/'project';project.mkdir();home=root/'memory'
            base=[sys.executable,str(ROOT/'tools/agent_memory.py')]
            subprocess.run(base+['init','--project',str(project),'--memory-home',str(home)],check=True,capture_output=True)
            pack=benchmark_pack(project);pack['cases']=[self.diagnosis,self.design]
            cases=root/'cases.json';cases.write_text(json.dumps(pack))
            before={str(p.relative_to(home)):p.read_bytes() for p in home.rglob('*') if p.is_file()}
            p=subprocess.run(base+['eval-agent-benchmark','--project',str(project),'--memory-home',str(home),'--cases',str(cases),'--runner','/nonexistent-runner','--json'],capture_output=True,text=True)
            self.assertNotEqual(p.returncode,0);self.assertIn('design-cache-policy',p.stderr)
            after={str(p.relative_to(home)):p.read_bytes() for p in home.rglob('*') if p.is_file()}
            self.assertEqual(before,after)
