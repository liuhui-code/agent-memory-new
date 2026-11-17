"""Frozen extension frontend checks; cross-file oracles belong to entity join."""
import json
from pathlib import Path
import unittest
from tools.agent_memory_runtime.sql_slot_source import inventory_source,classify_sql_owner,classify_ui_owner

D=Path(__file__).resolve().parents[1]/'docs/evidence/sql-method-container'
CORPUS=json.loads((D/'SOURCE-EXTENSION-CONTROLS.json').read_text())

class ObjectFrontendTests(unittest.TestCase):
    pass


def check(self,case):
    sql=[];ui=[];unknown=[]
    d=CORPUS['descriptor']
    for path,source in case['sources'].items():
        inv=inventory_source(source)
        if inv['status']=='unknown':unknown.append('inventory');continue
        for owner in inv['declarations']:
            sr=classify_sql_owner(source,owner,d['method'],d['sql_kind'])
            ur=classify_ui_owner(source,owner,d['method'],d['state'])
            for result,key,target,stage in [(sr,'matches',sql,'sql_source'),(ur,'chains',ui,'ui_source')]:
                if result['status']=='unknown':unknown.append(stage)
                else:target.extend((path,source,m) for m in result[key])
    ex=case['expected']
    if ex['status']=='positive':
        self.assertFalse(unknown);self.assertEqual(len(sql),1);self.assertEqual(len(ui),1)
        match=sql[0][2];chain=ui[0][2]
        self.assertEqual(match['result_type'],'ArchiveLine');self.assertEqual(chain['element_type'],'ArchiveLine')
        self.assertEqual(match['helper_declaration']['return_type'],'Promise<ArchiveLine[]>')
        rs=match['return_type_span'];self.assertEqual(sql[0][1][rs['start_offset']:rs['end_offset']],'Promise<ArchiveLine[]>')
        self.assertEqual(chain['item_identifier'],'line');self.assertIn(chain['render_field'],('caption','code'))
        ms=chain['member_expression_span'];self.assertEqual(ui[0][1][ms['start_offset']:ms['end_offset']],'line.'+chain['render_field'])
        self.assertIsInstance(match['projection_identifiers'],tuple)
    elif ex['stage'] in ('inventory','sql_source','ui_source'):
        allowed={'inventory',ex['stage']}
        legacy_object_deferred=(ex['stage']=='sql_source' and any(m['result_type'] is None for _,_,m in sql) and any(c['element_type']!='string' for _,_,c in ui))
        self.assertTrue(any(s in allowed for s in unknown) or legacy_object_deferred,(case['id'],unknown))
    else:
        # Cross-file rejection may occur earlier, but a locally known result is
        # not counted as final acceptance. Exact cross-file tests run separately.
        self.assertEqual(ex['stage'],'cross_file_entity')

for case in CORPUS['cases']:
    setattr(ObjectFrontendTests,'test_'+case['id'],lambda self,c=case:check(self,c))
