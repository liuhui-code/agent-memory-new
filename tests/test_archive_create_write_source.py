import json
from pathlib import Path
import unittest
from tools.agent_memory_runtime.archive_create_write_source import parse_archive_create_write as parse

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT/'tests/fixtures/archive_create_write.json'
A = '''import disk from '@ohos.file.fs';
export class PackageStager {
  async store(destination: string, payload: Uint8Array, output: string): Promise<void> {
    const opened = disk.openSync(destination, disk.OpenMode.CREATE);
    disk.writeSync(opened.fd, payload.buffer);
    disk.closeSync(opened);
    await unzip(destination, output);
  }
}
'''
B = '''import fileApi from '@ohos.file.fs'
class ResourceInstaller {
  async install(host: UIContext): Promise<void> {
    const content = host.resourceManager.getRawFileContentSync('resource.bin')
    const staging = host.tempDir + '/staging.data'
    const descriptor = fileApi.openSync(staging, fileApi.OpenMode.CREATE)
    fileApi.writeSync(descriptor.fd, content.buffer)
    fileApi.closeSync(descriptor)
    await unzip(staging, host.filesDir)
  }
}
'''


class ArchiveSourceTests(unittest.TestCase):
    def test_parameters_and_complete_spans(self):
        got = parse(A)
        self.assertEqual((got['owner'],got['start_line'],got['end_line']),('PackageStager',2,9))
        self.assertEqual([(m['name'],m['start_line'],m['end_line']) for m in got['methods']], [('store',3,8)])
        self.assertEqual(got['methods'][0]['handle'],'opened')

    def test_resource_compatibility(self):
        got = parse(B)
        self.assertEqual(got['methods'][0]['shape'],'resource')
        self.assertEqual((got['methods'][0]['start_line'],got['methods'][0]['end_line']),(3,10))
        original=(ROOT/'docs/eval/fixtures/system-capability/src/io/AssetArchiveInstaller.ets').read_text()
        self.assertIsNotNone(parse(original))

    def test_frozen_cohorts(self):
        p=json.loads(PROTOCOL.read_text())
        for label,c in p['cohorts'].items():
            positive={m['path'] for m in c['positive_methods']}
            for path,source in c['sources'].items():
                with self.subTest(cohort=label,path=path):
                    self.assertEqual(parse(source) is not None,path in positive)

    def test_whole_source_rejections(self):
        changes=[('CREATE','READ_ONLY'),('CREATE','CREATE | disk.OpenMode.TRUNC'),
                 ('opened.fd','destination.fd'),('disk.writeSync','other.writeSync'),
                 ('unzip(destination, output)','unzip(output, destination)'),
                 ('    await unzip(destination, output);\n',''),
                 ('disk.closeSync(opened)','disk.closeSync(payload)'),
                 ('const opened','let opened'),('payload.buffer','payload'),
                 ('@ohos.file.fs','other-module'),('Promise<void>','void'),
                 ('export class','export default class'),('const opened','const payload'),
                 ('payload: Uint8Array','disk: Uint8Array'),('payload: Uint8Array','unzip: Uint8Array'),
                 ('async store','async\nstore'),('class PackageStager','class unzip'),
                 ('import disk','import unzip'),('async store','async unzip'),
                 ('const opened','const unzip'),('const opened','const disk'),('const opened','const delete'),
                 ('destination: string','typeof: string'),
                 ('opened.fd','opened["fd"]'),('await unzip','unzip')]
        for old,new in changes:
            with self.subTest(old=old,new=new): self.assertIsNone(parse(A.replace(old,new)))
        for extra in ['const x = 1;', 'function unzip() {}', 'import another from "x";', '\u2028', '`unknown`', '/regex/']:
            with self.subTest(extra=extra): self.assertIsNone(parse(A+extra))
        self.assertIsNone(parse(A.replace('    const opened','    const alias = disk;\n    const opened')))
        self.assertIsNone(parse(A.replace('  async store','  field: string;\n  async store')))

    def test_order_and_asi(self):
        open_line='    const opened = disk.openSync(destination, disk.OpenMode.CREATE);\n'
        write_line='    disk.writeSync(opened.fd, payload.buffer);\n'
        self.assertIsNone(parse(A.replace(open_line+write_line,write_line+open_line)))
        self.assertIsNotNone(parse(A.replace(';','')))
        self.assertIsNone(parse(A.replace(';\n',' ')))
        self.assertIsNotNone(parse(A.replace('\n','\r\n')))
        self.assertIsNotNone(parse(A.replace('\n','\r')))

    def test_lexical_unknown_and_comments(self):
        self.assertIsNotNone(parse('/* archive fake unzip */\n'+A))
        self.assertIsNone(parse('/*'+A))
        self.assertIsNone(parse('//'+A.replace('\n',' ')))
        self.assertIsNone(parse('`'+A+'`'))
        self.assertIsNone(parse(B.replace("'resource.bin'",'`resource${x}`')))
        self.assertIsNone(parse(B.replace('staging, host.filesDir','content, host.filesDir')))
        self.assertIsNone(parse(B.replace('host.tempDir','other.tempDir')))
        self.assertIsNone(parse(B.replace('content.buffer','host.buffer')))

    def test_multiple_and_arbitrary_names(self):
        method=A[A.index('  async'):A.rindex('\n}')]
        self.assertEqual(len(parse(A.replace('\n}', '\n'+method.replace('store','save')+'\n}'))['methods']),2)
        self.assertIsNone(parse(A.replace('\n}', '\n'+method+'\n}')))
        renamed=A
        for a,b in [('disk','fileStore'),('PackageStager','BlobBundle'),('store(','persist('),('opened','descriptor'),('destination','scratch'),('payload','data'),('output','target')]: renamed=renamed.replace(a,b)
        self.assertIsNotNone(parse(renamed))
        self.assertIsNone(parse(A+B))
        self.assertIsNone(parse(A.replace('output: string','destination: string')))
        self.assertIsNone(parse(A.replace('class PackageStager {','class PackageStager extends Base {')))
        self.assertIsNone(parse(A.replace('  async store','  @Decorator\n  async store')))
        self.assertIsNone(parse(A.replace('  async store','  constructor() {}\n  async store')))
        self.assertIsNone(parse(A.replace('  async store','  async /*\n*/ store')))

    def test_input_limits(self):
        for value in [None,1,b'abc','\ud800', ' '*(2*1024*1024+1)+A]:
            self.assertIsNone(parse(value))


if __name__=='__main__': unittest.main()
