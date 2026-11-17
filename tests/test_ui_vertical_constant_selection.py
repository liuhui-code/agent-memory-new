"""Normal learned v3 literal binding controls; no evidence/output replay."""
from copy import deepcopy
from pathlib import Path
import tempfile,unittest
from unittest.mock import patch
from tests.command_table_test_support import prepare
from tests.test_ui_vertical_adjective_selection import ordinary,dbrows
from tests.archive_create_write_test_support import snapshot_database,restore_database
from tools.agent_memory_runtime.storage import connect
from tools.agent_memory_runtime.context_record_loop_transaction import restore_whitelist
from tools.agent_memory_runtime.query_ui_vertical_selection import bind_vertical_context,vertical_receipt,compact_vertical,accounting_vertical,VerticalContext
from tools.agent_memory_runtime.ui_vertical_inventory import inventory_vertical_file
SOURCE="@Component\nexport struct DocketLedger {\n  @State rows: string[] = []\n  build() {\n    Column() {\n      List() {\n        ForEach(this.rows, (row: string) => {\n          ListItem() {\n            Text(row)\n          }\n        })\n      }.listDirection(Axis.Vertical).height('100%')\n    }\n  }\n}\n"
CONST="export const DisplaySettings = { caption: 'Collection', columns: 2, highlighted: true, marker: null };\n"
def sources(subject,count,literal=True,prefix=None):
    names=[subject.capitalize()+'LedgerPane',subject.capitalize()+'ArchivePane'][:count]
    files={n+'.ets':SOURCE.replace('DocketLedger',n)for n in names}
    helper=SOURCE.replace('DocketLedger','QueueDisplayPane').replace('Text(row)','Text(DisplaySettings.caption)'if literal else "Text('Collection')")
    files['DisplayHelper.ets']=((CONST if prefix is None else prefix)if literal else '')+helper
    return files

def queries(subject):
    return [f'Locate the {subject} vertical layout source.',f'{subject.capitalize()} records cannot scroll when their content fills the viewport. Locate the vertical layout owner.']

class VerticalConstantSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup);cls.worlds={}
        for subject,count in [('maple',1),('cedar',2)]:
            for literal in (False,True):
                path=Path(cls.tmp.name)/(subject+str(literal));path.mkdir();project=prepare(path,sources=sources(subject,count,literal));saved=snapshot_database(project);cls.addClassCleanup(saved.close);cls.worlds[subject,literal]=project,saved,count
    def test_literal_pairs_full_identity_bodies_raw_accounting(self):
        for subject in ('maple','cedar'):
            project,saved,count=self.worlds[subject,True]
            for q in queries(subject):
                restore_database(project,saved);base,compact,pool=ordinary(project,q)
                self.assertIn('DisplayHelper.ets',{r.get('file_path')for r in pool})
                bound=bind_vertical_context(project,q,base,pool);self.assertIsInstance(bound,VerticalContext)
                self.assertEqual(dict(bound),base);self.assertEqual(accounting_vertical(bound),base)
                before=dbrows(project);out=compact_vertical(bound,compact);self.assertEqual(dbrows(project),before)
                self.assertEqual(restore_whitelist(out,compact),compact)
                self.assertEqual(out['query_handoff']['log_anchors'],compact['query_handoff']['log_anchors'])
                anchors=out['query_handoff']['code_anchors'];self.assertEqual(len(anchors),count)
                files=sources(subject,count);files.pop('DisplayHelper.ets');self.assertEqual({a['file_path']for a in anchors},set(files))
                for a in anchors:
                    row=next(r for r in pool if r.get('file_path')==a['file_path']and r.get('symbol')=='build')
                    self.assertEqual(a['record_ids'],[row['id']]);self.assertEqual(a['read_window'],{'start_line':4,'end_line':14})
                    self.assertEqual(a['source_excerpts'][0]['content'],'\n'.join(files[a['file_path']].splitlines()[3:14]))
                self.assertLessEqual(out['output_budget']['estimated_tokens'],1500)
    def test_four_inline_queries_exact_v2_transaction(self):
        actual=inventory_vertical_file
        def v2(source,**kwargs):return actual(source,allow_templates=kwargs.get('allow_templates',False))
        for subject in ('maple','cedar'):
            project,saved,_=self.worlds[subject,False]
            for q in queries(subject):
                restore_database(project,saved);base,compact,pool=ordinary(project,q)
                with patch('tools.agent_memory_runtime.ui_vertical_inventory.inventory_vertical_file',side_effect=v2):
                    bound=bind_vertical_context(project,q,base,pool);old=compact_vertical(bound,compact)
                new=bind_vertical_context(project,q,base,pool);self.assertIsInstance(new,VerticalContext)
                self.assertEqual(compact_vertical(new,compact),old)
    def test_explicit_v2_to_v3_transition(self):
        source=sources('maple',1)['DisplayHelper.ets']
        self.assertIsNone(inventory_vertical_file(source,allow_templates=True))
        inv=inventory_vertical_file(source,allow_templates=True,allow_literal_constants=True)
        self.assertIsNotNone(inv);self.assertTrue(any(d.name=='DisplaySettings'and d.kind=='literal_const'for d in inv.declarations))
    def test_real_pool_unknown_and_binding_controls(self):
        prefixes={
            'matching':"const CedarSettings = { caption: 'Collection' };\n",
            'critical':"const List = { caption: 'Collection' };\n",
            'duplicateclass':CONST+'class DisplaySettings {}\n',
            'duplicateimport':"import DisplaySettings from './settings';\n"+CONST,
            'call':"const DisplaySettings = { caption: makeCaption() };\n",
            'spread':"const DisplaySettings = { ...other };\n",
            'computed':"const DisplaySettings = { [key]: 'Collection' };\n",
            'alias':"const DisplaySettings = { caption: other };\n",
        }
        for label,prefix in prefixes.items():
            with self.subTest(label=label),tempfile.TemporaryDirectory()as t:
                project=prepare(t,sources=sources('cedar',2,prefix=prefix));q=queries('cedar')[0];base,compact,pool=ordinary(project,q)
                self.assertIn('DisplayHelper.ets',{r.get('file_path')for r in pool})
                self.assertIs(bind_vertical_context(project,q,base,pool),base)
    def test_same_matching_source_constant_stays_strict(self):
        files=sources('cedar',2,False);files['CedarLedgerPane.ets']+=CONST
        with tempfile.TemporaryDirectory()as t:
            project=prepare(t,sources=files);q=queries('cedar')[0];base,compact,pool=ordinary(project,q)
            self.assertIs(bind_vertical_context(project,q,base,pool),base)
    def test_helper_source_generation_and_new_binding_drift(self):
        project,saved,_=self.worlds['cedar',True];restore_database(project,saved);q=queries('cedar')[0];base,compact,pool=ordinary(project,q)
        bound=bind_vertical_context(project,q,base,pool);self.assertIsInstance(bound,VerticalContext)
        file=project.root/'DisplayHelper.ets';raw=file.read_bytes()
        try:
            file.write_bytes(raw+b"\nconst CedarExtra = { caption: 'Other' };\n")
            self.assertIsNone(vertical_receipt(bound));self.assertIs(bind_vertical_context(project,q,base,pool),base)
        finally:file.write_bytes(raw)
        self.assertIsNotNone(vertical_receipt(bound))
        with connect(project)as db:db.execute("UPDATE code_files SET index_generation=0 WHERE file_path='DisplayHelper.ets'")
        self.assertIsNone(vertical_receipt(bound))
