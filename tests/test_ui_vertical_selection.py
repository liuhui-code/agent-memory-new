"""Real learned pools for finite List selection; no recorded output replay."""
from copy import copy,deepcopy
from types import SimpleNamespace
import json,tempfile,unittest
from unittest.mock import patch
from tests.command_table_test_support import prepare
from tools.agent_memory_runtime.storage import connect
from tools.agent_memory_runtime.context_composition import build_context_facade
from tools.agent_memory_runtime.context_compact import compact_context
from tools.agent_memory_runtime.context_record_loop_transaction import restore_whitelist
from tools.agent_memory_runtime.query_ui_vertical_selection import (
    VerticalContext,bind_vertical_context,vertical_receipt,compact_vertical,enrich_vertical,
    accounting_vertical,binding)
Q='Locate the docket vertical layout source.'
SOURCE='''@Component
export struct DocketLedger {
  @State rows: string[] = []
  build() {
    Column() {
      List() {
        ForEach(this.rows, (row: string) => {
          ListItem() {
            Text(row)
          }
        })
      }.listDirection(Axis.Vertical).height('100%')
    }
  }
}
'''

def ordinary(project,query=Q):
    pools=[]
    def capture(_project,_query,baseline,pool):
        pools.append(deepcopy(pool));return baseline
    with patch('tools.agent_memory_runtime.query_ui_vertical_selection.bind_vertical_context',side_effect=capture):
        data=build_context_facade(project).execute(query);compact=compact_context(data)
    assert len(pools)==1,len(pools)
    return deepcopy(dict(data)),compact,pools[0]

class VerticalSelectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.project=prepare(self.tmp.name,sources={'DocketLedger.ets':SOURCE,'ParcelLedger.ets':SOURCE.replace('Docket','Parcel')})
        self.base,self.compact,self.pool=ordinary(self.project)
    def bind(self,pool=None,base=None):
        return bind_vertical_context(self.project,Q,self.base if base is None else base,self.pool if pool is None else pool)
    def test_complete_body_raw_noncode_and_accounting(self):
        bound=self.bind();self.assertIsInstance(bound,VerticalContext)
        self.assertEqual(dict(bound),self.base);self.assertEqual(accounting_vertical(bound),self.base)
        out=compact_vertical(bound,self.compact);self.assertIsNot(out,self.compact)
        self.assertEqual(restore_whitelist(out,self.compact),self.compact)
        self.assertEqual(out['query_handoff']['log_anchors'],self.compact['query_handoff']['log_anchors'])
        anchors=out['query_handoff']['code_anchors'];self.assertEqual(len(anchors),1)
        self.assertEqual(anchors[0]['source_excerpts'][0]['content'],'\n'.join(SOURCE.splitlines()[3:14]))
        self.assertLessEqual(out['output_budget']['estimated_tokens'],1500)
        def database_rows():
            with connect(self.project)as db:
                tables=[r[0]for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
                return {t:[tuple(r)for r in db.execute('SELECT * FROM "'+t.replace('"','""')+'"')]for t in tables}
        before=database_rows()
        accounting_vertical(bound);compact_vertical(bound,self.compact)
        after=database_rows()
        self.assertEqual(before,after)
    def test_each_typed_root_required(self):
        for kind,symbol in [('file','DocketLedger'),('symbol','DocketLedger'),('symbol','build')]:
            pool=[x for x in self.pool if not(x.get('file_path')=='DocketLedger.ets'and x.get('kind')==kind and x.get('symbol')==symbol)]
            self.assertLess(len(pool),len(self.pool));self.assertIs(self.bind(pool),self.base)
    def test_valid_receipt_cannot_replace_another_compact_baseline(self):
        bound=self.bind();self.assertIsInstance(bound,VerticalContext)
        self.assertIsNotNone(vertical_receipt(bound))
        self.assertIsNot(compact_vertical(bound,self.compact),self.compact)
        changed=deepcopy(self.compact);changed['query_handoff']['unrelated_note']='different baseline'
        result=compact_vertical(bound,changed)
        print('baseline-binding-repro', {'valid_receipt':True,'substituted':result is not changed})
        self.assertTrue(result is changed, 'A sealed receipt was applied to a non-normal compact baseline')
    def test_unindexed_second_subject_source_in_original_pool_is_not_hidden(self):
        with tempfile.TemporaryDirectory()as directory:
            project=prepare(directory,sources={'DocketOne.ets':SOURCE.replace('DocketLedger','DocketOne'),
                                              'DocketTwo.ets':SOURCE.replace('DocketLedger','DocketTwo')})
            base,compact,pool=ordinary(project)
            complete=bind_vertical_context(project,Q,base,pool)
            self.assertIsInstance(complete,VerticalContext)
            self.assertEqual(len(complete._anchors),2)
            with connect(project)as db:
                removed={r['id']for r in db.execute("SELECT id FROM code_symbols WHERE file_path='DocketTwo.ets' AND (symbol='DocketTwo' OR symbol='build')")}
                self.assertEqual(len(removed),2)
                db.execute("DELETE FROM code_symbols WHERE file_path='DocketTwo.ets' AND (symbol='DocketTwo' OR symbol='build')")
            incomplete=[r for r in pool if not(r['kind']=='symbol'and r['id']in removed)]
            self.assertTrue(any(r['kind']=='file'and r['file_path']=='DocketTwo.ets'for r in incomplete))
            self.assertTrue(any(r.get('symbol')=='build'and r['file_path']=='DocketOne.ets'for r in incomplete))
            with connect(project)as db:
                self.assertIsNotNone(db.execute("SELECT id FROM code_files WHERE file_path='DocketTwo.ets'").fetchone())
            result=bind_vertical_context(project,Q,base,incomplete)
            print('source-scope-omission-repro', {'issued':isinstance(result,VerticalContext),
                  'served_paths':[a['file_path']for a in result._anchors]if isinstance(result,VerticalContext)else[]})
            self.assertTrue(result is base, 'A missing second subject owner/build was silently omitted')
    def test_source_drift(self):
        bound=self.bind();self.assertIsInstance(bound,VerticalContext)
        (self.project.root/'DocketLedger.ets').write_text(SOURCE+'\n')
        self.assertIsNone(vertical_receipt(bound));self.assertIs(self.bind(),self.base)
    def test_generation_and_alias(self):
        bound=self.bind();self.assertIsInstance(bound,VerticalContext)
        with connect(self.project)as db:
            db.execute("UPDATE code_symbols SET index_generation=0 WHERE file_path='DocketLedger.ets'")
        self.assertIsNone(vertical_receipt(bound));self.assertIs(self.bind(),self.base)
    def test_db_key_alias(self):
        with connect(self.project)as db:
            row=dict(db.execute("SELECT * FROM code_symbols WHERE file_path='DocketLedger.ets' AND symbol='build'").fetchone());row.pop('id')
            row['file_path']='Other.ets';row['qualified_name']='Other.build';row['owner_name']='Other'
            db.execute('INSERT INTO code_symbols ('+','.join(row)+') VALUES ('+','.join('?'for _ in row)+')',list(row.values()))
        self.assertIs(self.bind(),self.base)
    def test_copy_and_mutation_even_recomputed_binding(self):
        bound=self.bind();self.assertIsInstance(bound,VerticalContext)
        for fake in (dict(bound),copy(bound),deepcopy(bound),json.loads(json.dumps(bound))):self.assertIsNone(vertical_receipt(fake))
        bound._anchors[0]['record_ids'][0]+=100;bound._binding=binding(bound)
        self.assertIsNone(vertical_receipt(bound))
        bound=self.bind();bound['query']='changed';bound._binding=binding(bound);self.assertIsNone(vertical_receipt(bound))
    def test_project_guard(self):
        bound=self.bind();self.assertIsInstance(bound,VerticalContext)
        bound._project=SimpleNamespace(root=self.project.root,db_path=self.project.db_path,project_id='different')
        bound._binding=binding(bound);self.assertIsNone(vertical_receipt(bound))
        base=deepcopy(self.base);base['project_path']=str(self.project.root/'elsewhere');self.assertIs(self.bind(base=base),base)
    def test_identity_graph_log_path_and_event_guards(self):
        for flag in ('identity_match','log_identity_match','graph_neighbor','graph_relation'):
            base=deepcopy(self.base);base['query_handoff']['code_anchors'][0][flag]=True
            self.assertIs(self.bind(base=base),base,flag)
        log={'log_id':999,'evidence_class':'direct','message_template':'background pulse complete','logger':'console','file_path':'PulseService.ts','function':'emit','line':3}
        base=deepcopy(self.base);base['query_handoff']['log_anchors']=[log]
        bound=self.bind(base=base);self.assertIsInstance(bound,VerticalContext)
        compact=deepcopy(self.compact);compact['query_handoff']['log_anchors']=[deepcopy(log)]
        out=compact_vertical(bound,compact)
        # Artificial log insertion leaves ordinary sufficiency metadata unchanged:
        # atomic fallback is allowed, but no log/noncode field may be discarded.
        self.assertEqual(out['query_handoff']['log_anchors'],[log]);self.assertEqual(restore_whitelist(out,compact),compact)
        from tools.agent_memory_runtime.log_event_identity import event_match
        strong=deepcopy(log);strong['message_template']=Q
        self.assertGreater(event_match(strong,Q)['priority'],0)
        base=deepcopy(self.base);base['query_handoff']['log_anchors']=[strong]
        self.assertIs(self.bind(base=base),base)
        base=deepcopy(self.base);base['query_handoff']['log_anchors']=[dict(log,log_identity_match=True)]
        self.assertIs(self.bind(base=base),base)
        bound=self.bind();path=deepcopy(self.base['query_handoff']['path_context']);path['activated']=True
        self.assertNotIsInstance(enrich_vertical(bound,Q,path,self.base['source_freshness']),VerticalContext)
        query=Q+' Explain the event.';self.assertIs(bind_vertical_context(self.project,query,self.base,self.pool),self.base)
    def test_real_oversize_transaction_falls_back(self):
        bound=self.bind();self.assertIsInstance(bound,VerticalContext)
        huge=deepcopy(self.compact);huge['query_handoff']['preserved_note']='real preserved payload '*2000
        self.assertIs(compact_vertical(bound,huge),huge)
    def test_three_complete_positive_and_four_fallback(self):
        for count in (3,4):
            with tempfile.TemporaryDirectory()as t:
                names=['DocketAlpha','DocketBeta','DocketGamma','DocketDelta'][:count]
                sources={name+'.ets':SOURCE.replace('DocketLedger',name)for name in names}
                project=prepare(t,sources=sources);base,compact,pool=ordinary(project)
                bound=bind_vertical_context(project,Q,base,pool)
                if count==4:self.assertIs(bound,base)
                else:
                    self.assertIsInstance(bound,VerticalContext)
                    self.assertEqual(len(vertical_receipt(bound)),3)
                    out=compact_vertical(bound,compact)
                    self.assertIsNot(out,compact)
                    self.assertEqual({x['file_path']for x in out['query_handoff']['code_anchors']},set(sources))
    def test_actual_facade_compact_two_positives_and_accounting_parity(self):
        from tests.archive_create_write_test_support import snapshot_database,restore_database
        import time
        with tempfile.TemporaryDirectory()as t:
            sources={name+'.ets':SOURCE.replace('DocketLedger',name)for name in ('DocketAlpha','DocketBeta')}
            project=prepare(t,sources=sources)
            saved=snapshot_database(project);self.addCleanup(saved.close)
            def accounting_rows():
                result={}
                with connect(project)as db:
                    for table in ('projects','project_counters','query_misses','experience_usage_events','reflection_reuse_events','episodes','semantic_facts','reflections'):
                        columns=[r[1]for r in db.execute('PRAGMA table_info('+table+')')]
                        if not columns:continue
                        keep=[c for c in columns if c not in ('created_at','updated_at','last_used_at','reviewed_at','occurred_at','timestamp')]
                        result[table]=[tuple(r)for r in db.execute('SELECT '+','.join('"'+c+'"'for c in keep)+' FROM "'+table+'"')]
                return result
            # Cross the storage timestamp resolution deliberately: a receipt may
            # not silently expire merely because normal accounting updates time.
            time.sleep(1.05)
            ordinary_raw,ordinary_compact,_=ordinary(project)
            ordinary_rows=accounting_rows()
            restore_database(project,saved)
            time.sleep(1.05)
            raw=build_context_facade(project).execute(Q)
            after_execute=accounting_rows()
            out=compact_context(raw)
            self.assertEqual(dict(raw),ordinary_raw)
            self.assertEqual(after_execute,ordinary_rows)
            self.assertEqual(accounting_rows(),after_execute)
            self.assertNotEqual(out,ordinary_compact)
            self.assertEqual(restore_whitelist(out,ordinary_compact),ordinary_compact)
            anchors=out['query_handoff']['code_anchors']
            self.assertEqual({a['file_path']for a in anchors},set(sources))
            self.assertEqual(len(anchors),2)
            for anchor in anchors:
                self.assertEqual(anchor['source_excerpts'][0]['content'],'\n'.join(sources[anchor['file_path']].splitlines()[3:14]))
            self.assertLessEqual(out['output_budget']['estimated_tokens'],1500)
            self.assertEqual(compact_context(raw),out)
            self.assertEqual(accounting_rows(),after_execute)
    def test_inventory_helper_real_pool_and_complete_two_targets(self):
        helper='''export class CaptionCache {
  private count: number = 0
  constructor() { this.count = 1 }
  async refresh(): Promise<void> { this.count = this.count + 1 }
  caption(value: string): string { return value }
}
'''+SOURCE.replace('DocketLedger','InventoryListPane').replace('  build() {','  private cache: CaptionCache = new CaptionCache()\n  build() {').replace('Text(row)','Text(this.cache.caption(row))')
        with tempfile.TemporaryDirectory()as t:
            sources={'DocketAlpha.ets':SOURCE.replace('DocketLedger','DocketAlpha'),
                     'DocketBeta.ets':SOURCE.replace('DocketLedger','DocketBeta'),'InventoryListPane.ets':helper}
            project=prepare(t,sources=sources);base,compact,pool=ordinary(project)
            self.assertIn('InventoryListPane.ets',{r.get('file_path')for r in pool})
            bound=bind_vertical_context(project,Q,base,pool);self.assertIsInstance(bound,VerticalContext)
            out=compact_vertical(bound,compact)
            self.assertEqual({a['file_path']for a in out['query_handoff']['code_anchors']},{'DocketAlpha.ets','DocketBeta.ets'})
            self.assertEqual(restore_whitelist(out,compact),compact)
            (project.root/'InventoryListPane.ets').write_text(helper+'\n')
            self.assertIsNone(vertical_receipt(bound))
    def test_inventory_unknown_helpers_really_in_original_pool(self):
        controls={
            'regex':"export class PatternCache { pattern = /ready/ }\n",
            'nested':"export class PatternCache { value(): number { class HiddenHelper {} return 1 } }\n",
            'typeonly':"import type { PatternCache } from './cache';\n",
            'subjectalias':"import { Driver as DocketDriver } from './cache';\n",
            'criticalalias':"import { Driver as List } from './cache';\n",
        }
        for label,prefix in controls.items():
            with self.subTest(label=label),tempfile.TemporaryDirectory()as t:
                helper=prefix+SOURCE.replace('DocketLedger','InventoryListPane')
                project=prepare(t,sources={'DocketLedger.ets':SOURCE,'InventoryListPane.ets':helper})
                base,compact,pool=ordinary(project)
                self.assertIn('InventoryListPane.ets',{r.get('file_path')for r in pool},label+' control not covered')
                self.assertIs(bind_vertical_context(project,Q,base,pool),base)
    def test_remote_import_subject_is_not_local_binding(self):
        helper="import { DocketDriver as CacheDriver } from './cache';\n"+SOURCE.replace('DocketLedger','InventoryListPane')
        with tempfile.TemporaryDirectory()as t:
            project=prepare(t,sources={'DocketLedger.ets':SOURCE,'InventoryListPane.ets':helper})
            base,compact,pool=ordinary(project)
            self.assertIn('InventoryListPane.ets',{r.get('file_path')for r in pool})
            bound=bind_vertical_context(project,Q,base,pool)
            self.assertIsInstance(bound,VerticalContext)
    def test_same_file_unknown_and_source_only_matching_cannot_hide(self):
        for suffix in ('\nexport class PatternCache { label = `ready` }\n',
                       '\n'+SOURCE.replace('DocketLedger','DocketHidden')):
            with tempfile.TemporaryDirectory()as t:
                project=prepare(t,sources={'DocketLedger.ets':SOURCE+suffix})
                if 'DocketHidden'in suffix:
                    with connect(project)as db:
                        db.execute("DELETE FROM code_symbols WHERE symbol='DocketHidden' OR owner_name='DocketHidden'")
                base,compact,pool=ordinary(project)
                self.assertIn('DocketLedger.ets',{r.get('file_path')for r in pool})
                self.assertIs(bind_vertical_context(project,Q,base,pool),base)
    def test_inventory_helper_generation_stays_receipt_bound(self):
        helper=SOURCE.replace('DocketLedger','InventoryListPane')
        with tempfile.TemporaryDirectory()as t:
            project=prepare(t,sources={'DocketLedger.ets':SOURCE,'InventoryListPane.ets':helper})
            base,compact,pool=ordinary(project);bound=bind_vertical_context(project,Q,base,pool)
            self.assertIsInstance(bound,VerticalContext)
            with connect(project)as db:db.execute("UPDATE code_files SET index_generation=0 WHERE file_path='InventoryListPane.ets'")
            self.assertIsNone(vertical_receipt(bound))
    def test_real_source_byte_resource_boundaries(self):
        # Real bytes, not patched limit constants; comments add no bindings.
        def padded(text,size):
            remaining=size-len(text.encode())
            self.assertGreaterEqual(remaining,5)
            value=text+'/*'+'x'*(remaining-5)+'*/\n'
            self.assertEqual(len(value.encode()),size)
            return value
        mib=1024*1024
        for size,accepted in ((2*mib,True),(2*mib+1,False)):
            with self.subTest(boundary='file',size=size),tempfile.TemporaryDirectory()as t:
                project=prepare(t,sources={'DocketLedger.ets':padded(SOURCE,size)})
                base,compact,pool=ordinary(project)
                self.assertIn('DocketLedger.ets',{r.get('file_path')for r in pool})
                bound=bind_vertical_context(project,Q,base,pool)
                if accepted:self.assertIsInstance(bound,VerticalContext)
                else:self.assertIs(bound,base)
        for extra,accepted in ((0,True),(1,False)):
            with self.subTest(boundary='aggregate',extra=extra),tempfile.TemporaryDirectory()as t:
                sources={'DocketLedger.ets':SOURCE}
                # Four genuinely recalled List helper paths; each remains <=2MiB.
                sizes=[2*mib,2*mib,2*mib,2*mib-len(SOURCE.encode())+extra]
                for owner,size in zip(('CatalogPanel','InboxPanel','ArchivePanel','ReceiptPanel'),sizes):
                    sources[owner+'.ets']=padded(SOURCE.replace('DocketLedger',owner),size)
                self.assertEqual(sum(len(v.encode())for v in sources.values()),8*mib+extra)
                self.assertTrue(all(len(v.encode())<=2*mib for v in sources.values()))
                project=prepare(t,sources=sources);base,compact,pool=ordinary(project)
                self.assertEqual({r.get('file_path')for r in pool},set(sources),'resource control requires all actual admitted paths')
                bound=bind_vertical_context(project,Q,base,pool)
                if accepted:self.assertIsInstance(bound,VerticalContext)
                else:self.assertIs(bound,base)
    def test_v1_raw_template_control_explicit_v2_transition(self):
        from tools.agent_memory_runtime.ui_vertical_inventory import inventory_vertical_file
        # Exact prior unknown-control bytes, not resampled after the new parser.
        helper="export class PatternCache { label = `ready` }\n"+SOURCE.replace('DocketLedger','InventoryListPane')
        self.assertIsNone(inventory_vertical_file(helper))
        self.assertIsNotNone(inventory_vertical_file(helper,allow_templates=True))
        with tempfile.TemporaryDirectory()as t:
            project=prepare(t,sources={'DocketLedger.ets':SOURCE,'InventoryListPane.ets':helper})
            base,compact,pool=ordinary(project)
            self.assertIn('InventoryListPane.ets',{r.get('file_path')for r in pool})
            raw=build_context_facade(project).execute(Q);out=compact_context(raw)
            self.assertIsInstance(raw,VerticalContext)
            # Query accounting may differ between sequential calls; source-view
            # binding itself must leave every raw field untouched.
            bound=bind_vertical_context(project,Q,base,pool)
            self.assertEqual(dict(bound),base)
            manual=compact_vertical(bound,compact)
            self.assertEqual(restore_whitelist(manual,compact),compact)
            self.assertEqual(manual['query_handoff']['log_anchors'],compact['query_handoff']['log_anchors'])
            for value in (out,manual):
                anchors=value['query_handoff']['code_anchors'];self.assertEqual(len(anchors),1)
                self.assertEqual(anchors[0]['file_path'],'DocketLedger.ets')
                self.assertEqual(anchors[0]['source_excerpts'][0]['content'],'\n'.join(SOURCE.splitlines()[3:14]))
    def test_admitted_template_plain_pairs_complete_source_identity(self):
        from tools.agent_memory_runtime.ui_vertical_inventory import inventory_vertical_file
        for subject,count in (('maple',1),('cedar',2)):
            plain_identities=None
            for template in (False,True):
                with self.subTest(subject=subject,template=template),tempfile.TemporaryDirectory()as t:
                    names=[subject.capitalize()+'LedgerPane',subject.capitalize()+'ArchivePane'][:count]
                    sources={name+'.ets':SOURCE.replace('DocketLedger',name)for name in names}
                    helper=SOURCE.replace('DocketLedger','QueueDisplayPane')
                    if template:helper=helper.replace('Text(row)','Text(`Queued: ${row}`)')
                    sources['DisplayHelper.ets']=helper
                    if template:
                        self.assertIsNone(inventory_vertical_file(helper))
                        self.assertIsNotNone(inventory_vertical_file(helper,allow_templates=True))
                    project=prepare(t,sources=sources);query='Locate the '+subject+' vertical layout source.'
                    base,compact,pool=ordinary(project,query)
                    self.assertIn('DisplayHelper.ets',{r.get('file_path')for r in pool})
                    bound=bind_vertical_context(project,query,base,pool);self.assertIsInstance(bound,VerticalContext)
                    self.assertEqual(dict(bound),base)
                    out=compact_vertical(bound,compact)
                    self.assertEqual(restore_whitelist(out,compact),compact)
                    anchors=out['query_handoff']['code_anchors'];self.assertEqual(len(anchors),count)
                    self.assertEqual({a['file_path']for a in anchors},{n+'.ets'for n in names})
                    identities=[]
                    for anchor in anchors:
                        self.assertEqual(anchor['source_excerpts'][0]['content'],'\n'.join(sources[anchor['file_path']].splitlines()[3:14]))
                        row=next(r for r in pool if r.get('kind')=='symbol'and r['id']==anchor['record_ids'][0]and r['file_path']==anchor['file_path'])
                        identities.append((row['file_path'],row['qualified_name'],row['source_digest'],row['start_line'],row['end_line']))
                    if not template:plain_identities=sorted(identities)
                    else:self.assertEqual(sorted(identities),plain_identities)
    def test_v2_unknown_template_controls_admitted_pool(self):
        from tools.agent_memory_runtime.ui_vertical_inventory import inventory_vertical_file
        helper=SOURCE.replace('DocketLedger','InventoryListPane')
        controls={
            'call':helper.replace('Text(row)','Text(`Queued: ${String(row)}`)'),
            'tagged':helper.replace('Text(row)','Text(format`Queued: ${row}`)'),
            'nested':helper.replace('Text(row)','Text(`Queued: ${`nested`}`)'),
            'declaration':helper.replace('Text(row)','Text(`Queued: ${class Hidden {}}`)'),
            'regex':helper.replace('Text(row)','Text(`Queued: ${/ready/}`)'),
            'unknown-neighbor':helper.replace('Text(row)','Text(`Queued: ${row}`)')+'\nexport class PatternCache { pattern = /ready/ }\n',
        }
        for label,text in controls.items():
            with self.subTest(label=label),tempfile.TemporaryDirectory()as t:
                self.assertIsNone(inventory_vertical_file(text,allow_templates=True))
                project=prepare(t,sources={'DocketLedger.ets':SOURCE,'DisplayHelper.ets':text})
                base,compact,pool=ordinary(project)
                self.assertIn('DisplayHelper.ets',{r.get('file_path')for r in pool},'unknown not actually covered')
                self.assertIs(bind_vertical_context(project,Q,base,pool),base)
        late=helper.replace('Text(row)','Text(`Queued: ${row}`)')+'\n'+SOURCE.replace('DocketLedger','DocketLatePane')
        with tempfile.TemporaryDirectory()as t:
            self.assertIsNotNone(inventory_vertical_file(late,allow_templates=True))
            project=prepare(t,sources={'DocketLedger.ets':SOURCE,'DisplayHelper.ets':late})
            base,compact,pool=ordinary(project)
            self.assertIn('DisplayHelper.ets',{r.get('file_path')for r in pool})
            self.assertTrue(any(r.get('owner_name')=='DocketLatePane'and r.get('symbol')=='build'for r in pool))
            self.assertIs(bind_vertical_context(project,Q,base,pool),base)
