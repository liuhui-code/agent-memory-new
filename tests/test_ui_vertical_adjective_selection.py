"""Focused adjective-slot controls; real learned pools, no evidence-output replay."""
from copy import copy,deepcopy
import tempfile,unittest
from unittest.mock import patch
from tests.command_table_test_support import prepare
from tests.archive_create_write_test_support import snapshot_database,restore_database
from tools.agent_memory_runtime.storage import connect
from tools.agent_memory_runtime.context_composition import build_context_facade
from tools.agent_memory_runtime.context_compact import compact_context
from tools.agent_memory_runtime.context_record_loop_transaction import restore_whitelist
from tools.agent_memory_runtime.query_record_loop_selection import protected_record_loop
from tools.agent_memory_runtime.query_ui_vertical_guard import protected_vertical
from tools.agent_memory_runtime.query_ui_vertical_selection import (VerticalContext,bind_vertical_context,vertical_receipt,compact_vertical,enrich_vertical,accounting_vertical,binding)
SOURCE="@Component\nexport struct DocketLedger {\n  @State rows: string[] = []\n  build() {\n    Column() {\n      List() {\n        ForEach(this.rows, (row: string) => {\n          ListItem() {\n            Text(row)\n          }\n        })\n      }.listDirection(Axis.Vertical).height('100%')\n    }\n  }\n}\n"
def query(subject):
    return f'The viewport clips {subject} records and the vertical layout does not move. Return the current code owner.'
def sources(subject,count,method,event=False):
    names=[subject.capitalize()+'LedgerPane',subject.capitalize()+'ArchivePane'][:count]
    result={name+'.ets':SOURCE.replace('DocketLedger',name)for name in names}
    import json
    prefix='export class LabelCache {\n  '+method+'(value: string): string {\n'
    if event:prefix+='    console.info('+json.dumps(query(subject))+')\n'
    prefix+='    return value\n  }\n}\n'
    result['DisplayHelper.ets']=prefix+SOURCE.replace('DocketLedger','QueueDisplayPane').replace('  build() {','  private cache: LabelCache = new LabelCache()\n  build() {').replace('Text(row)','Text(this.cache.'+method+'(row))')
    return result

def ordinary(project,q):
    pools=[]
    def capture(_p,_q,base,pool):pools.append(deepcopy(pool));return base
    with patch('tools.agent_memory_runtime.query_ui_vertical_selection.bind_vertical_context',side_effect=capture):
        raw=build_context_facade(project).execute(q);compact=compact_context(raw)
    assert len(pools)==1
    return deepcopy(dict(raw)),compact,pools[0]

def dbrows(project):
    with connect(project)as db:
        names=[r[0]for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        return {n:[tuple(r)for r in db.execute('SELECT * FROM "'+n.replace('"','""')+'"')]for n in names}

class VerticalAdjectiveSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
        from pathlib import Path
        cls.worlds={}
        for subject,count in [('maple',1),('cedar',2)]:
            for method in ('ordinary','current'):
                root=Path(cls.tmp.name)/(subject+'-'+method);root.mkdir()
                project=prepare(root,sources=sources(subject,count,method));saved=snapshot_database(project);cls.addClassCleanup(saved.close)
                cls.worlds[subject,method]=(project,saved,count)
        root=Path(cls.tmp.name)/'event';root.mkdir();project=prepare(root,sources=sources('cedar',2,'current',True));saved=snapshot_database(project);cls.addClassCleanup(saved.close);cls.event=(project,saved)
    def world(self,subject='cedar',method='current'):
        project,saved,count=self.worlds[subject,method];restore_database(project,saved)
        q=query(subject);base,compact,pool=ordinary(project,q)
        return project,q,base,compact,pool,count
    def test_current_single_double_complete_original_ids_and_body(self):
        for subject in ('maple','cedar'):
            project,q,base,compact,pool,count=self.world(subject)
            self.assertTrue(any(r.get('symbol')=='current'for r in pool))
            self.assertTrue(protected_record_loop(base,q,pool))
            self.assertFalse(protected_vertical(base,q,pool))
            bound=bind_vertical_context(project,q,base,pool);self.assertIsInstance(bound,VerticalContext)
            self.assertEqual(dict(bound),base);self.assertEqual(accounting_vertical(bound),base)
            before=dbrows(project);out=compact_vertical(bound,compact)
            self.assertEqual(dbrows(project),before)
            self.assertEqual(restore_whitelist(out,compact),compact)
            self.assertEqual(out['query_handoff']['log_anchors'],compact['query_handoff']['log_anchors'])
            anchors=out['query_handoff']['code_anchors'];self.assertEqual(len(anchors),count)
            expected=sources(subject,count,'current');expected.pop('DisplayHelper.ets')
            self.assertEqual({a['file_path']for a in anchors},set(expected))
            for a in anchors:
                target=next(r for r in pool if r.get('file_path')==a['file_path']and r.get('symbol')=='build')
                self.assertEqual(a['record_ids'],[target['id']]);self.assertEqual(a['read_window'],{'start_line':4,'end_line':14})
                self.assertEqual(a['source_excerpts'][0]['content'],'\n'.join(expected[a['file_path']].splitlines()[3:14]))
            self.assertLessEqual(out['output_budget']['estimated_tokens'],1500)
    def test_ordinary_pairs_equal_old_transaction(self):
        for subject in ('maple','cedar'):
            project,q,base,compact,pool,count=self.world(subject,'ordinary')
            self.assertFalse(protected_record_loop(base,q,pool));self.assertFalse(protected_vertical(base,q,pool))
            with patch('tools.agent_memory_runtime.query_ui_vertical_selection.protected_vertical',side_effect=protected_record_loop):
                old=bind_vertical_context(project,q,base,pool);oldout=compact_vertical(old,compact)
            new=bind_vertical_context(project,q,base,pool)
            self.assertEqual(compact_vertical(new,compact),oldout)
    def test_actual_event_world_stays_ordinary(self):
        project,saved=self.event;restore_database(project,saved);q=query('cedar');base,compact,pool=ordinary(project,q)
        self.assertTrue(protected_record_loop(base,q,pool));self.assertTrue(protected_vertical(base,q,pool))
        self.assertIs(bind_vertical_context(project,q,base,pool),base)
    def test_receipt_copy_query_and_resealed_tamper(self):
        project,q,base,compact,pool,_=self.world()
        bound=bind_vertical_context(project,q,base,pool);self.assertIsInstance(bound,VerticalContext)
        for fake in (dict(bound),copy(bound),deepcopy(bound)):self.assertIsNone(vertical_receipt(fake))
        bound['query']=q+' extra';bound._binding=binding(bound);self.assertIsNone(vertical_receipt(bound))
        bound=bind_vertical_context(project,q,base,pool);bound._anchors[0]['record_ids'][0]+=100;bound._binding=binding(bound);self.assertIsNone(vertical_receipt(bound))
    def test_source_and_generation_drift(self):
        project,q,base,compact,pool,_=self.world();bound=bind_vertical_context(project,q,base,pool)
        path=project.root/'DisplayHelper.ets';original=path.read_bytes()
        try:
            path.write_bytes(original+b'\n');self.assertIsNone(vertical_receipt(bound))
        finally:path.write_bytes(original)
        self.assertIsNotNone(vertical_receipt(bound))
        with connect(project)as db:db.execute("UPDATE code_files SET index_generation=0 WHERE file_path='DisplayHelper.ets'")
        self.assertIsNone(vertical_receipt(bound))
    def test_late_path_and_log_fault_injection(self):
        # Unit mutation only: not a normal public log experiment.
        project,q,base,compact,pool,_=self.world();bound=bind_vertical_context(project,q,base,pool)
        path=deepcopy(base['query_handoff']['path_context']);path['activated']=True
        self.assertNotIsInstance(enrich_vertical(bound,q,path,base['source_freshness']),VerticalContext)
        for flag in ('identity_match','log_identity_match','graph_neighbor','graph_relation'):
            modified=deepcopy(base);modified['query_handoff']['code_anchors'][0][flag]=True
            self.assertIs(bind_vertical_context(project,q,modified,pool),modified)
        modified=deepcopy(base);modified['query_handoff']['log_anchors']=[{'log_id':99,'message_template':q,'file_path':'Notice.ts','function':'emit','line':3,'evidence_class':'direct'}]
        self.assertTrue(protected_vertical(modified,q,pool));self.assertIs(bind_vertical_context(project,q,modified,pool),modified)
        bound['query_handoff']['log_anchors']=modified['query_handoff']['log_anchors'];bound._binding=binding(bound)
        self.assertNotIsInstance(enrich_vertical(bound,q,base['query_handoff']['path_context'],base['source_freshness']),VerticalContext)
