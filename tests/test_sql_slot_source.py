"""Frozen complete-source contract controls, no CLI or evaluator invocation."""
import json
from pathlib import Path
import unittest
from tools.agent_memory_runtime.sql_slot_source import inventory_source, classify_sql_owner, classify_ui_owner

CORPUS=Path(__file__).resolve().parents[1]/'docs/evidence/sql-method-container/SOURCE-CONTROLS.json'

class SourceControls(unittest.TestCase):
    pass


def check_case(self,case):
    d=case['request']['descriptor']; expected=case['expected']
    seen=set(); methods_by_path={}
    for path,source in case['sources'].items():
        inv=inventory_source(source)
        self.assertEqual(inv['status'],expected['inventory'][path],(case['id'],path,inv.get('reason')))
        if inv['status']!='known': continue
        methods_by_path[path]=[m for o in inv['declarations'] for m in o['methods']]
        for owner in inv['declarations']:
            seen.add(owner['name'])
            for domain,fn,args,key in [('sql_owner',classify_sql_owner,(d['method'],d['sql_kind']),'matches'),('ui_owner',classify_ui_owner,(d['method'],d['state']),'chains')]:
                result=fn(source,owner,*args)
                actual='unknown' if result['status']=='unknown' else 'positive' if result[key] else 'known_empty'
                self.assertEqual(actual,expected[domain][owner['name']],(case['id'],owner['name'],domain,result))

    for w in expected.get('complete_method_witnesses',[]):
        candidates=[m for m in methods_by_path[w['file_path']] if m['name']==w['symbol']]
        self.assertEqual(len(candidates),1)
        m=candidates[0]; sp=m['span']; source=case['sources'][w['file_path']]
        self.assertEqual((sp['start_line'],sp['end_line']),(w['start_line'],w['end_line']))
        lines=source.splitlines(keepends=True)
        exact=''.join(lines[sp['start_line']-1:sp['end_line']]).rstrip('\r\n')
        self.assertEqual(exact,w['exact_excerpt'])
        self.assertEqual(source[sp['start_offset']:sp['end_offset']],exact.lstrip(' \t'))

for case in json.loads(CORPUS.read_text())['source_cases']:
    setattr(SourceControls,'test_'+case['id'],lambda self,c=case:check_case(self,c))

if __name__=='__main__': unittest.main()
