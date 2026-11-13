# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,tempfile
from pathlib import Path
from types import SimpleNamespace
from tests.agent_memory_test_base import AgentMemoryTestBase
from tools.agent_memory_runtime.callable_behavior_hints import callable_behavior_hints

class CallableCacheHintTests(AgentMemoryTestBase):
    def protocol(self):
        return json.loads((Path(__file__).resolve().parents[1]/'docs/evidence/cache-eviction-current/protocol.json').read_text())

    def hints(self,source):
        return callable_behavior_hints(SimpleNamespace(name='trim',file_path='Pool.ts'),source)

    def test_same_method_conjunction_and_unknown_nested_scope(self):
        source='trim(limit:number){ if(this.pool.size>limit){ for(const [key,row] of this.pool){ if(row.timestamp<100){this.pool.delete(key)} } } }'
        self.assertIn('cacheeviction',self.hints(source))
        for code in [
            "trim(){return 'this.pool.size for(const row of pool) row.timestamp this.pool.delete(key)'}",
            'trim(){queueMicrotask(()=>{'+source+'})}',
            'trim(){const bag={ ["go"](){'+source+'} }}',
            'trim(){const sample=`${flag ? `'+source+'` : ""}`}',
            'trim(){if(this.pool.size>1){for(const row of this.pool){use(row.timestamp)}}}',
            'trim(){this.pool.delete(key)}',
            'trim(){if(this.pool.size>1){this.pool.delete(this.pool.keys().next().value)}}',
        ]:
            with self.subTest(code=code):self.assertNotIn('cacheeviction',self.hints(code))

    def test_public_executable_source_not_string_monitor(self):
        p=self.protocol()
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for name,source in p['sources'].items():(root/name).write_text(source)
            self.run_memory(root,'init');self.run_memory(root,'learn-path','--path','.')
            for item in p['queries'][:2]:
                out=json.loads(self.run_memory(root,'context','--query',item['query'],'--compact','--json').stdout)
                anchors=out['query_handoff']['code_anchors']
                self.assertIn('ExpiryStore.ts',{a['file_path'] for a in anchors})
                self.assertNotEqual('CacheMonitor.ts',(out['query_handoff']['callable_evidence'].get('primary') or {}).get('file_path'))
