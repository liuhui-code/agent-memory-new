from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from tools.agent_memory_runtime.web_policy_reading_source import web_policy_chains
from tools.agent_memory_runtime.context_web_policy_reading import web_reading_request, web_reading_order
from tools.agent_memory_runtime.context_composition import build_context_facade
from tools.agent_memory_runtime.context_compact import compact_context
from tools.agent_memory_runtime.context_callable_envelope import expand_callable_envelopes
from tools.agent_memory_runtime.storage import resolve_project, connect
from tests.archive_create_write_test_support import cli
ROOT=Path(__file__).resolve().parents[1]
P=json.loads((ROOT/'docs/evidence/web-policy-reading/protocol.json').read_text())
Q=P['queries']['positive']

class WebPolicyReadingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.temp.cleanup);cls.samples={}
        for name in ('positive','two-web','opposite-value'):
            root=Path(cls.temp.name)/name;root.mkdir()
            for path,text in P['sources'][name].items():
                f=root/path;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(text)
            p=resolve_project(str(root),str(Path(cls.temp.name)/(name+'-memory')))
            cli(p,'init');cli(p,'learn-path','--path','.','--json')
            raw=deepcopy(dict(build_context_facade(p).execute(Q)));base=expand_callable_envelopes(p,compact_context(deepcopy(raw)),enabled=True)
            cls.samples[name]=(p,raw,base)
    def sample(self,name='positive'):
        p,r,b=self.samples[name];return p,deepcopy(r),deepcopy(b)
    def test_closed_source_controls(self):
        expected={'positive':[1,0],'two-web':[1,0,1],'split-chain':[0,0],'ordinary-object':[None],'opposite-value':[1,0],'literal-only':[0]}
        for name,files in P['sources'].items():
            found=[web_policy_chains(s)for s in files.values()]
            self.assertEqual([None if f is None else len(f) for f in found],expected[name])
    def test_request_controls_and_composition(self):
        for name,q in P['queries'].items():self.assertEqual(web_reading_request(q),name=='positive')
        for q in ['Locate executable WebView file access and URL navigation policy source.','An in-app WebView blocks file navigation. Locate the executable access and navigation policy implementation.']:
            self.assertTrue(web_reading_request(q))
        for extra in [' not Reader',' compare both',' metadata',' logs',' Settings','\n']:
            self.assertFalse(web_reading_request(Q+extra))
    def test_positive_preserves_every_old_candidate_and_other_field(self):
        p,r,b=self.sample();a=web_reading_order(p,r,b)
        self.assertIsNot(a,b)
        old=b['query_handoff']['callable_evidence'];new=a['query_handoff']['callable_evidence']
        self.assertEqual(new['primary']['file_path'],'src/web/Reader.ets')
        before=[old['primary'],*old['alternatives']];after=[new['primary'],*new['alternatives']]
        self.assertEqual([after[i]for i in new['reading_basis']['prior']],before)
        self.assertEqual(new['certainty'],'uncertain')
        restored=deepcopy(a);restored['query_handoff']['callable_evidence']=old;restored['output_budget']=b['output_budget'];self.assertEqual(restored,b)
        self.assertIs(web_reading_order(p,r,a),a)
    def test_actual_cli(self):
        p,_,_=self.sample();a=json.loads(cli(p,'context','--query',Q,'--compact','--json'))
        self.assertEqual(a['query_handoff']['callable_evidence']['primary']['file_path'],'src/web/Reader.ets')
        self.assertIn('reading_basis',a['query_handoff']['callable_evidence'])
    def test_two_implementations_noop_even_when_body_hidden(self):
        p,r,b=self.sample('two-web');self.assertIs(web_reading_order(p,r,b),b)
        b['query_handoff']['code_anchors']=[a for a in b['query_handoff']['code_anchors'] if a['file_path']!='src/web/OtherReader.ets']
        self.assertIs(web_reading_order(p,r,b),b)
    def test_opposite_setting_same_proof(self):
        p,r,b=self.sample('opposite-value');a=web_reading_order(p,r,b)
        # Frozen public true-setting output omits the complete build body;
        # the guard must not be weakened to make the control switch.
        self.assertIs(a,b)
        source=(Path(p.root)/'src/web/Reader.ets').read_text()
        for anchor in b['query_handoff']['code_anchors']:
            if anchor['file_path']=='src/web/Reader.ets':
                anchor['source_excerpts']=[dict(start_line=8,end_line=18,content='\n'.join(source.splitlines()[7:18]))]
        b['output_budget']['target_tokens']=2000
        a=web_reading_order(p,r,b)
        self.assertIsNot(a,b);self.assertEqual(a['query_handoff']['callable_evidence']['primary']['file_path'],'src/web/Reader.ets')
    def test_budget_missing_body_raw_identity_stale(self):
        for change in ('budget','body','raw','generation','graph'):
            p,r,b=self.sample()
            if change=='budget':b['output_budget']['target_tokens']=1
            if change=='body':b['query_handoff']['code_anchors']=[]
            if change=='raw':r['query_handoff']['callable_evidence']['alternatives']=[]
            if change=='generation':b['source_freshness']['generation']+=1
            if change=='graph':b['query_handoff']['path_context']['activated']=True
            self.assertIs(web_reading_order(p,r,b),b,change)
    def test_changed_source(self):
        p,r,b=self.sample();file=Path(p.root)/'src/web/Reader.ets';old=file.read_bytes()
        try:
            file.write_bytes(old+b'\n');self.assertIs(web_reading_order(p,r,b),b)
        finally:file.write_bytes(old)
    def test_nested_shadow_and_duplicate_chain(self):
        source=P['sources']['positive']['src/web/Reader.ets']
        for s in [source.replace('const url =','const Web ='),source.replace('struct Reader','struct web_webview'),source.replace('Web({','this.Web({'),source.replace('.fileAccess(false)','.fileAccess(false).fileAccess(true)'),source.replace("'@ohos.web.webview'","'other-sdk'")]:
            self.assertIsNone(web_policy_chains(s))
        double=source+source[source.index('@Component'):].replace('Reader','Other')
        self.assertEqual(len(web_policy_chains(double)),2)

    def test_corrupted_nonpositive_candidate_owner_kind(self):
        p,r,b=self.sample()
        for e in [r['query_handoff']['callable_evidence'],b['query_handoff']['callable_evidence']]:
            for c in [e['primary'],*e['alternatives']]:
                if c['owner_name']=='Settings': c['owner_kind']='class'
        with connect(p) as db:
            db.execute("UPDATE code_symbols SET owner_kind='class' WHERE file_path='src/pages/Settings.ets'")
        try:self.assertIs(web_reading_order(p,r,b),b)
        finally:
            with connect(p) as db:db.execute("UPDATE code_symbols SET owner_kind='component' WHERE file_path='src/pages/Settings.ets'")
