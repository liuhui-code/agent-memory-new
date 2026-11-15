# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
from tests.agent_memory_test_base import AgentMemoryTestBase


def source(parameters='business: string, text: string', body='void business\n    Logger.info(text)', args="'business value', 'real message'", receiver='this.emit'):
    return ('export class Courier {\n'
            f'  emit({parameters}): void {{\n    {body}\n  }}\n'
            f'  run(): void {{\n    {receiver}({args})\n  }}\n}}\n')


class DirectSinkBindingTests(AgentMemoryTestBase):
    def public_case(self, text):
        with tempfile.TemporaryDirectory() as temporary:
            project=Path(temporary)/'project'; project.mkdir()
            (project/'Courier.ts').write_text(text)
            self.run_memory(project,'init'); self.run_memory(project,'wiki-index')
            results=[]
            for extra in [(),('--compact',)]:
                handoff=json.loads(self.run_memory(project,'context','--query',
                    'Courier run emit real message business value Logger.info',*extra,'--json').stdout)['query_handoff']
                results.append([a for a in handoff['log_anchors'] if a.get('function')=='run'])
            return results

    def test_frozen_public_ordinals(self):
        cases=[
            ('first',source('text: string, business: string','void business\n    Logger.info(text)',"'real message', 'business value'"),'real message'),
            ('second',source(),'real message'),
            ('third',source('a: string, b: number, payload: string','void a\n    void b\n    Logger.info(payload)',"'business value', 3, 'real message'"),'real message'),
            ('empty',source(args="'business value', ''"),''),
            ('nonliteral',source(args="'business value', externalText"),'{text}'),
            ('reassigned',source(body="text = 'changed'\n    Logger.info(text)"),'{text}'),
            ('default',source(parameters="business: string, text: string = 'fallback'"),'{text}'),
        ]
        for label,text,expected in cases:
            with self.subTest(label=label):
                for anchors in self.public_case(text):
                    self.assertEqual(1,len(anchors))
                    self.assertEqual(expected,anchors[0]['message_template'])
                    self.assertEqual(['run','emit','logger.info'],anchors[0]['call_path'])
                    self.assertEqual(1,anchors[0]['wrapper_depth'])

    def test_bounded_binding_negative_controls(self):
        # Exercise the source/identity receipt independently of query ranking.
        from tools.agent_memory_runtime.direct_sink_binding import direct_message_binding
        from tools.agent_memory_runtime.log_effects import wrapper_call_candidates, call_message
        from tools.agent_memory_runtime.storage import resolve_project
        cases={
            'alias':source(body='const alias = text\n    Logger.info(alias)'),
            'two_sinks':source(body='Logger.info(text)\n    Logger.info(business)'),
            'rest':source(parameters='business: string, ...text: string[]'),
            'duplicate':source(parameters='text: string, text: string',body='Logger.info(text)'),
            'arity':source(args="'business value'"),
            'spread':source(args="...values"),
            'escaped':source(args=r"'business value', 'real\nmessage'"),
            'template':source(args="'business value', `real ${value}`"),
            'regex':source(args="/,/.source, 'real message'"),
            'comment_argument':source(args="'business value' /* , */, 'real message'"),
            'generic_argument':source(args="make<A, B>(), 'real message'"),
            'other_receiver':source(receiver='other.emit'),
            'same_name':source().replace('  run():', '  emit(business: string, text: string): void { Logger.info(text) }\n  run():'),
            'local_shadow':source(body="{ let text = 'other'; Logger.info(text) }"),
        }
        for label,text in cases.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                project=Path(temporary)/'project';project.mkdir();(project/'Courier.ts').write_text(text)
                self.run_memory(project,'init');self.run_memory(project,'wiki-index')
                with sqlite3.connect(self.project_memory_dir(project)/'memory.db') as conn:
                    conn.row_factory=sqlite3.Row
                    for item in wrapper_call_candidates(conn,self.project_id(project),None):
                        if item['caller']!='run': continue
                        _, raw=call_message(project,item,{})
                        result=direct_message_binding(conn,self.project_id(project),project,item,raw,{})
                        self.assertNotEqual('real message',result)
                        self.assertNotEqual('business value',result)

    def test_identity_and_source_mutations_refuse(self):
        from tools.agent_memory_runtime.direct_sink_binding import direct_message_binding
        from tools.agent_memory_runtime.log_effects import wrapper_call_candidates, call_message
        with tempfile.TemporaryDirectory() as temporary:
            project=Path(temporary)/'project';project.mkdir();path=project/'Courier.ts';path.write_text(source())
            self.run_memory(project,'init');self.run_memory(project,'wiki-index')
            with sqlite3.connect(self.project_memory_dir(project)/'memory.db') as conn:
                conn.row_factory=sqlite3.Row
                item=next(i for i in wrapper_call_candidates(conn,self.project_id(project),None) if i['caller']=='run')
                _,raw=call_message(project,item,{})
                self.assertEqual('real message',direct_message_binding(conn,self.project_id(project),project,item,raw,{}))
                for key,value in [('caller_id',0),('wrapper_id',0),('source_digest',''),('index_generation',0),('wrapper_depth',2),('evidence_class','inferred_wrapped')]:
                    with self.subTest(key=key):
                        self.assertNotEqual('real message',direct_message_binding(conn,self.project_id(project),project,{**item,key:value},raw,{}))
                for sql in ["UPDATE code_symbols SET source_digest = '' WHERE symbol='emit'", "UPDATE code_symbols SET index_generation=99 WHERE symbol='emit'", "UPDATE code_symbols SET owner_name='Other' WHERE symbol='emit'", "UPDATE code_symbols SET qualified_name='Other.emit' WHERE symbol='emit'"]:
                    conn.execute('SAVEPOINT guard');conn.execute(sql)
                    self.assertNotEqual('real message',direct_message_binding(conn,self.project_id(project),project,item,raw,{}))
                    conn.execute('ROLLBACK TO guard');conn.execute('RELEASE guard')
                path.write_text(source().replace('Logger.info(text)','Logger.info(business)'))
                self.assertNotEqual('real message',direct_message_binding(conn,self.project_id(project),project,item,raw,{}))
