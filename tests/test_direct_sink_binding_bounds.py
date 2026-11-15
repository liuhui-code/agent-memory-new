# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
from __future__ import annotations
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch
from tests.agent_memory_test_base import AgentMemoryTestBase
from tests.test_direct_sink_binding import source
from tools.agent_memory_runtime.direct_sink_binding import direct_message_binding, source_snapshot, legacy_source_text, MAX_SOURCE_BYTES
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
            reads.clear(); cache={}
            with patch.object(Path,'open',counted):
                self.assertEqual('source',legacy_source_text(root,'x.ts',cache))
                self.assertIsNotNone(source_snapshot(root,'x.ts',cache))
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

    def test_distinct_owner_same_name_producer_refuses_ambiguity(self):
        text=source()+'''export class Another {
  emit(text: string): void {
    Logger.info(text)
  }
}
'''
        # Existing producer emits no call edge for these same-file names.
        # This is a producer refusal control, not a successful binding receipt.
        self.assertEqual([],self.binding(text))

    def test_shadow_and_multihop_never_gain_concrete_receipt(self):
        controls=[
            source(parameters='Logger: string, text: string',body='Logger.info(text)'),
            source().replace('export class Courier {','export class Courier {\n  private Logger: Object'),
            source().replace('export class Courier {','export class Courier { private Logger: Object;'),
            source().replace('export class Courier {','export class Courier {\n  relay(a: string, b: string): void { this.emit(a,b) }').replace("this.emit('business value'", "this.relay('business value'"),
            source(parameters='{business}: Object, text: string'),
            source(parameters='business: string, text?: string'),
            source(body='void business Logger.info(text)'),
            source(parameters='while: string, text: string',body='Logger.info(text)'),
            source(parameters='package: string, text: string',body='Logger.info(text)'),
            source(args="new, 'real message'"),
            source(args="throw, 'real message'"),
            source().replace('export class Courier {', 'export class Courier {\n  constructor() { this.emit = () => {} }'),
            source().replace('export class Courier {', 'export class Courier {\n  emit = () => {}'),
            source().replace('export class Courier {', 'export class Courier {\n  get emit() { return () => {} }'),
            source().replace('export class Courier {', 'export class Courier extends Base {'),
            source().replace('export class Courier {', 'export class Courier {\n  reset() { this.emit = other }'),
        ]
        for text in controls:
            with self.subTest(text=text):
                self.assertTrue(all(x not in ('real message','business value') for x in self.binding(text)))

    def test_legacy_large_and_invalid_bytes_keep_raw_call(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);path=root/'Courier.ts'
            call="this.emit('business', 'real message')"
            item={'file_path':'Courier.ts','line':1,'wrapper':'emit'}
            for data in [(call+'\n'+' '*(MAX_SOURCE_BYTES+1)).encode(),call.encode()+b'\n\xff']:
                path.write_bytes(data)
                legacy=call_message(root,item,{})
                cache={}
                self.assertEqual(legacy,call_message(root,item,{},cache))
                self.assertIsNone(source_snapshot(root,'Courier.ts',cache))
                self.assertFalse(any(key[0]=='legacy_source' for key in cache))

    def test_arguments_reject_bare_keywords(self):
        from tools.agent_memory_runtime.direct_sink_binding import _arguments
        for word in ('new', 'return', 'throw', 'if', 'while', 'package'):
            with self.subTest(word=word):
                self.assertIsNone(_arguments("this.emit("+word+", 'real message')"))
        self.assertEqual(['business', "'real message'"], _arguments("this.emit(business, 'real message')"))

    def test_unrelated_owner_members_preserve_public_first_parameter(self):
        from tests.test_direct_sink_binding import DirectSinkBindingTests
        base=source('text: string, business: string','void business\n    Logger.info(text)',"'real message', 'business value'")
        for addition in ['\n  unrelated(): void {}', '\n  private counter: number = 0']:
            with self.subTest(addition=addition):
                text=base.replace('export class Courier {','export class Courier {'+addition)
                for anchors in DirectSinkBindingTests().public_case(text):
                    self.assertEqual(['real message'],[a.get('message_template') for a in anchors])

    def test_complex_non_message_argument_preserves_public_message(self):
        from tests.test_direct_sink_binding import DirectSinkBindingTests
        text=source('text: string, business: string','void business\n    Logger.info(text)',"'real message', computeBusiness()")
        for anchors in DirectSinkBindingTests().public_case(text):
            self.assertEqual(['real message'],[a.get('message_template') for a in anchors])

    def test_same_file_candidates_share_one_read_and_line_split(self):
        from tools.agent_memory_runtime import log_effects
        text=source().replace('emit','emitOne').replace('run','runOne')
        text+=source().replace('Courier','Parcel').replace('emit','emitTwo').replace('run','runTwo')
        with tempfile.TemporaryDirectory() as temporary:
            project=Path(temporary)/'project';project.mkdir();path=project/'Courier.ts';path.write_text(text)
            self.run_memory(project,'init');self.run_memory(project,'wiki-index')
            with sqlite3.connect(self.project_memory_dir(project)/'memory.db') as conn:
                conn.row_factory=sqlite3.Row
                items=wrapper_call_candidates(conn,self.project_id(project),None)
                self.assertEqual({'runOne','runTwo'},{i['caller'] for i in items})
                reads=[];splits=[];original_open=Path.open;original_text=log_effects.legacy_source_text
                class CountedText(str):
                    def splitlines(self,*args,**kwargs):
                        splits.append(1);return super().splitlines(*args,**kwargs)
                def counted_open(path,*args,**kwargs):
                    reads.append(path);return original_open(path,*args,**kwargs)
                def counted_text(*args,**kwargs):
                    return CountedText(original_text(*args,**kwargs))
                line_cache={};cache={}
                with patch.object(Path,'open',counted_open),patch.object(log_effects,'legacy_source_text',counted_text):
                    for item in items:
                        _,raw=call_message(project,item,line_cache,cache)
                        self.assertEqual('real message',direct_message_binding(conn,self.project_id(project),project,item,raw,cache))
                self.assertEqual([path],reads)
                self.assertEqual([1],splits)
                self.assertIs(cache[('lines','Courier.ts')],line_cache['Courier.ts'])
