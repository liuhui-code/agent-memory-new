# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

"""Self-contained AFTER regression importing the actual production parser.
One unittest method covers five subtests; full seven-field BEFORE/AFTER delta
comparison belongs to the separate evidence runner, not this regression.
"""
import copy
import hashlib

FIELDS = {'path', 'text', 'digest', 'entities', 'relations', 'mechanisms', 'gaps'}
CASES = ('local-resolved', 'local-missing', 'typed-known', 'typed-missing', 'imported-receiver')

def require(ok, reason):
    if not ok:
        raise ValueError(reason)

def check_case(case, value, source, phase):
    require(set(value) == FIELDS, 'ParsedFile exact seven fields')
    require(value['path'] == 'src/' + case + '.ets', 'source path')
    require(value['text'] == source.decode('utf-8'), 'source text')
    require(value['digest'] == hashlib.sha256(source).hexdigest(), 'source digest')
    for field in ('entities', 'relations', 'mechanisms', 'gaps'):
        require(type(value[field]) is list, 'list ' + field)
    gaps = {'local-resolved':['this.helper'], 'local-missing':['missing','this.missing'],
            'typed-known':[], 'typed-missing':['service.load'], 'imported-receiver':[]}[case]
    if phase == 'after':
        gaps = [g for g in gaps if g not in ('this.helper','this.missing')]
    expected = [{'kind':'unresolved_await_target','file_path':value['path'],'symbol':g} for g in gaps]
    require(value['gaps'] == expected, 'complete ordered gaps ' + case)
    owners = [e for e in value['entities'] if e['qualified_name'] == 'AwaitOwner.run']
    require(len(owners) == 1, 'unique actual caller entity')
    edges = [r for r in value['relations'] if r['source_key'] == owners[0]['key']]
    if case == 'local-resolved':
        targets = [e for e in value['entities'] if e['qualified_name'] == 'AwaitOwner.helper']
        require(len(targets) == 1, 'unique actual local target entity')
        for kind in ('calls','awaits'):
            require(len([r for r in edges if r['relation']==kind and r['target_key']==targets[0]['key']]) == 1, 'local exact target ' + kind)
    if case in ('typed-known','imported-receiver'):
        target = 'AwaitService.load' if case=='typed-known' else 'ImportedService.load'
        for kind in ('calls','awaits'):
            matched=[r for r in edges if r['relation']==kind and r['target_qualified_name']==target]
            require(len(matched)==1, 'typed exact target ' + kind)
            if case=='imported-receiver':
                require(matched[0]['target_file_path']=='src/ImportedService.ets', 'actual import path')
    if case in ('local-missing','typed-missing'):
        require(not [r for r in edges if r['relation'] in ('calls','awaits')], 'no fabricated missing target edge')

def compare_after(before, after):
    require(list(before)==list(CASES) and list(after)==list(CASES), 'exact five case order')
    for case in CASES:
        expected=copy.deepcopy(before[case])
        if case in ('local-resolved','local-missing'):
            symbol='this.helper' if case=='local-resolved' else 'this.missing'
            gap={'kind':'unresolved_await_target','file_path':expected['path'],'symbol':symbol}
            require(expected['gaps'].count(gap)==1, 'exact one removable gap')
            expected['gaps'].remove(gap)
        require(after[case]==expected, 'all seven fields, list order and duplicates unchanged except exact gap: '+case)


import tempfile
import unittest
from pathlib import Path
from dataclasses import asdict
from tools.agent_memory_runtime.semantic_ecma import parse_source
from tools.agent_memory_runtime.models import Project

FIXTURES = {'ImportedService.ets': 'export class ImportedService {\n  static async load(): Promise<void> {}\n}\n', 'imported-receiver.ets': "import { ImportedService } from './ImportedService'\nexport class AwaitOwner {\n  async run(): Promise<void> {\n    await ImportedService.load()\n  }\n}\n", 'local-missing.ets': 'export class AwaitOwner {\n  async run(): Promise<void> {\n    await this.missing()\n  }\n}\n', 'local-resolved.ets': 'export class AwaitOwner {\n  async helper(): Promise<void> {}\n  async run(): Promise<void> {\n    await this.helper()\n  }\n}\n', 'typed-known.ets': 'class AwaitService {\n  async load(): Promise<void> {}\n}\nexport class AwaitOwner {\n  private service: AwaitService = new AwaitService()\n  async run(): Promise<void> {\n    await this.service.load()\n  }\n}\n', 'typed-missing.ets': 'export class AwaitOwner {\n  async run(): Promise<void> {\n    await this.service.load()\n  }\n}\n'}

class LocalAwaitClassificationRegression(unittest.TestCase):
    def test_exact_five_after_contracts(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'src').mkdir()
            for name,text in FIXTURES.items():
                (root/'src'/name).write_bytes(text.encode('utf-8'))
            project=Project(root,root/'no-home',root/'no-memory',root/'no-db',root/'no-vault',root/'no-runtime','await-regression','await-regression')
            for case in CASES:
                with self.subTest(case=case):
                    data=FIXTURES[case+'.ets'].encode('utf-8')
                    actual=asdict(parse_source(project,root/'src'/(case+'.ets'),data,'ArkTS',True))
                    check_case(case,actual,data,'after')

if __name__ == '__main__':
    unittest.main()
