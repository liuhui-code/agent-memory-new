"""Finite optional lexical selection; no public-world or authority claims."""
import copy
import hashlib
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from tools.agent_memory_runtime import query_literal_property as nav
from tools.agent_memory_runtime.literal_property_source import read_literal_source


class LiteralPropertyNavigationTests(unittest.TestCase):
    def rows(self):
        return [dict(id=i, project_id='p', file_path='Plan.ts', symbol='run',
                     symbol_key=f'key{i}', source_digest='a'*64,index_generation=1,
                     start_line=i*3,end_line=i*3+2,literal_property_path=f'Plan.{part}.run',
                     source_count=2,graph_depth=0,owner_kind='object',owner_name='Plan',
                     localization_score=1,evidence_score=1,localization_reasons=[],
                     callable_roles='[]') for i,part in [(1,'first'),(2,'second')]]

    def apply(self, query, rows=None):
        rows=self.rows() if rows is None else rows
        with patch.object(nav,'fresh',return_value=True):
            return nav.prefer_literal_property(None,query,rows,[{'file_path':'Plan.ts'}],rows,list(rows))

    def test_full_request_and_identity_preservation(self):
        for query in ['Locate Plan.second.run.','Locate `Plan.second.run`.']:
            rows=self.rows(); before=copy.deepcopy(rows)
            result=self.apply(query,rows)
            self.assertEqual([r['id'] for r in result],[2,1]);self.assertIs(result[0],rows[1])
            self.assertEqual(rows,before)
        for query in ['Locate run.','Locate Plan.Second.run.','Locate Plan.second.',
                      'Do not Locate Plan.second.run.','Locate Plan.second.run except first.',
                      'Locate Plan.second.run compared with first.','Locate Plan.second.run and explain.']:
            self.assertEqual([r['id'] for r in self.apply(query)],[1,2])

    def test_complete_pool_and_protected_precedence(self):
        for field,value in [('source_count',3),('typed_contract_weak',True),
                            ('typed_contract_match',True),('source_operation_match',True),
                            ('artifact_role_competition',True),('excluded_by_query',True),
                            ('explicit_owner_identity_match',True),('target_owner_kind_match',True)]:
            rows=self.rows();rows[0][field]=value
            self.assertEqual([r['id'] for r in self.apply('Locate Plan.second.run.',rows)],[1,2])
        rows=self.rows();rows[0]['literal_property_path']=rows[1]['literal_property_path']
        self.assertEqual([r['id'] for r in self.apply('Locate Plan.second.run.',rows)],[1,2])
        rows=self.rows();rows[1]['evidence_score']=10
        self.assertEqual([r['id'] for r in self.apply('Locate Plan.second.run.',rows)],[1,2])
        rows=self.rows()
        with patch.object(nav,'fresh',return_value=False):
            result=nav.prefer_literal_property(None,'Locate Plan.second.run.',rows,[{'file_path':'Plan.ts'}],rows,rows)
        self.assertIs(result,rows)
        with patch.object(nav,'fresh',return_value=True):
            chosen=[rows[0]]
            self.assertIs(nav.prefer_literal_property(None,'Locate Plan.second.run.',rows,[{'file_path':'Plan.ts'}],rows,chosen),chosen)

    def test_bounded_source_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=SimpleNamespace(root=root);f=root/'a.ts'
            for size in [1,65536]:
                f.write_bytes(b'x'*size);self.assertEqual(read_literal_source(p,'a.ts'),b'x'*size)
            f.write_bytes(b'x'*65537);self.assertIsNone(read_literal_source(p,'a.ts'))
            (root/'link').symlink_to(f);self.assertIsNone(read_literal_source(p,'link'))
            os.mkfifo(root/'pipe');self.assertIsNone(read_literal_source(p,'pipe'))
            self.assertIsNone(read_literal_source(p,'../a.ts'))
            self.assertIsNone(read_literal_source(p,'.'))

    def test_fresh_metadata_binding(self):
        closed=[]
        class Connection:
            def close(self):closed.append(True)
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def execute(self,sql,args):self.sql=sql;return self
            def fetchmany(self,n):return [state] if 'code_index_state' in self.sql else [file]
        raw=b'fixed';digest=hashlib.sha256(raw).hexdigest();row=self.rows()[0]
        row['source_digest']=digest
        state={'status':'active','generation':2};file={'source_digest':digest,'index_generation':1}
        with patch.object(nav,'connect',return_value=Connection()),patch.object(nav,'read_literal_source',return_value=raw):
            self.assertTrue(nav.fresh(SimpleNamespace(project_id='p'),row))
            self.assertEqual(closed,[True])
            for key,value in [('source_digest','b'*64),('index_generation',2)]:
                old=file[key];file[key]=value
                self.assertFalse(nav.fresh(SimpleNamespace(project_id='p'),row));file[key]=old
            state['status']='retired';self.assertFalse(nav.fresh(SimpleNamespace(project_id='p'),row))
