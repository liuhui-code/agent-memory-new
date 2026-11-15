# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
from __future__ import annotations
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch
from tests.agent_memory_test_base import AgentMemoryTestBase
from tests.test_direct_sink_binding import source
from tools.agent_memory_runtime.direct_sink_binding import direct_message_binding, source_snapshot, MAX_SOURCE_BYTES
from tools.agent_memory_runtime.log_effects import wrapper_call_candidates, call_message


class DirectSinkBindingBoundsTests(AgentMemoryTestBase):
    def test_source_cache_reads_once_and_caps(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); path=root/'x.ts';path.write_text('source')
            cache={}; original=Path.open; reads=[]
            def counted(path,*args,**kwargs):
                reads.append(path);return original(path,*args,**kwargs)
            with patch.object(Path,'open',counted):
                self.assertEqual(source_snapshot(root,'x.ts',cache),source_snapshot(root,'x.ts',cache))
            self.assertEqual([path],reads)
            path.write_bytes(b'x'*(MAX_SOURCE_BYTES+1))
            self.assertIsNone(source_snapshot(root,'x.ts',{}))
            path.write_bytes(b'\xff')
            self.assertIsNone(source_snapshot(root,'x.ts',{}))
            self.assertIsNone(source_snapshot(root,'../escape.ts',{}))

    def binding(self,text):
        with tempfile.TemporaryDirectory() as temporary:
            project=Path(temporary)/'project';project.mkdir();(project/'Courier.ts').write_text(text)
            self.run_memory(project,'init');self.run_memory(project,'wiki-index')
            with sqlite3.connect(self.project_memory_dir(project)/'memory.db') as conn:
                conn.row_factory=sqlite3.Row
                records=[]
                for item in wrapper_call_candidates(conn,self.project_id(project),None):
                    if item['caller']!='run':continue
                    _,raw=call_message(project,item,{})
                    records.append(direct_message_binding(conn,self.project_id(project),project,item,raw,{}))
                return records

    def test_distinct_owner_same_name_does_not_redirect(self):
        text=source()+'''export class Another {
  emit(text: string): void {
    Logger.info(text)
  }
}
'''
        self.assertEqual(['real message'],self.binding(text))

    def test_shadow_and_multihop_never_gain_concrete_receipt(self):
        controls=[
            source(parameters='Logger: string, text: string',body='Logger.info(text)'),
            source().replace('export class Courier {','export class Courier {\n  private Logger: Object'),
            source().replace('export class Courier {','export class Courier {\n  relay(a: string, b: string): void { this.emit(a,b) }').replace("this.emit('business value'", "this.relay('business value'"),
            source(parameters='{business}: Object, text: string'),
            source(parameters='business: string, text?: string'),
        ]
        for text in controls:
            with self.subTest(text=text):
                self.assertTrue(all(x not in ('real message','business value') for x in self.binding(text)))
