import ast,json,tempfile
from pathlib import Path
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.query_intent_contract import infer_memory_intent_v2, resolve_memory_intent

TESTS=Path(__file__).resolve().parent

def procedure_fixture():
    tree=ast.parse((TESTS/'test_explicit_context_intent.py').read_text())
    return next(ast.literal_eval(n.value)for n in ast.walk(tree)if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='payload'for t in n.targets))

class LogIntentWordBoundaryTests(AgentMemoryTestBase):
    def test_nonlogging_words_do_not_change_source_intent(self):
        for term in ('dialog','catalog','dialogue','analog','logarithm','prologue','analogy','catalogue','backlog','login','logout','logical','CatalogEntry','DialogController'):
            with self.subTest(term=term):self.assertEqual('code_location',infer_memory_intent_v2(f'Locate {term} source.'))

    def test_log_terms_and_identifiers_keep_existing_route(self):
        for term in ('log','LOGS','logging','logger','loggers','hilog','syslog','logcat','LogSink','CacheLogger','cache_log','event_log','LOG_EVENT_123','console.log','日志','exception','failed','failure'):
            with self.subTest(term=term):self.assertEqual('runtime_log_diagnosis',infer_memory_intent_v2(f'Locate {term} source.'))
        self.assertEqual('code_business_semantics',infer_memory_intent_v2('What does log mean?'))
        self.assertEqual('semantic_correction',infer_memory_intent_v2('Correct misleading log advice.'))
        self.assertEqual('memory_maintenance',infer_memory_intent_v2('Refresh log source.'))
        self.assertEqual('code_location',resolve_memory_intent('Locate log source.','code_location')[1])

    def test_public_unrelated_word_does_not_admit_refresh_procedure(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            self.run_memory(root,'reflect','--payload',json.dumps(procedure_fixture()))
            for term in ('','catalog ','dialog '):
                for mode in ([],['--compact']):
                    d=json.loads(self.run_memory(root,'context','--query',f'Locate {term}cache file source.','--json',*mode).stdout)
                    self.assertEqual('code_location',d.get('memory_intent_v2',d['memory_intent']))
                    self.assertEqual([],d['query_handoff']['experience_refs'])
            d=json.loads(self.run_memory(root,'context','--query','Locate log cache file source.','--json','--compact').stdout)
            self.assertEqual('runtime_log_diagnosis',d['memory_intent'])
            self.assertEqual(1,d['query_handoff']['experience_refs'][0]['reflection_id'])
