# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,subprocess,sys,os
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO=Path(os.environ.get('RUNTIME_REPO',ROOT.parent/'language-priority-investigation'))
FILES={
'src/InvoiceExporter.ets':'''export class InvoiceExporter {
  exportInvoice(context: UIContext): string {
    const directory = context.filesDir
    return directory + '/invoice.json'
  }
}
''',
'src/PaletteParser.ets':'''export class PaletteParser {
  parseColor(value: string): number {
    const digits = value.replace('#', '')
    return Number.parseInt(digits, 16)
  }
}
''',
'src/RuntimeLogger.ets':'''export class RuntimeLogger {
  report(message: string): void {
    console.error(message)
  }
}
'''}
QUERIES=[
'请定位 invoice export 的 ArkTS 实现。',
'请查找 invoice export 的 ArkTS 实现。',
'请定位 palette parse color 的源码实现。',
'请查找 palette parse color 的源码实现。',
'请定位错误日志的输出入口。',
'请定位 RuntimeLogger.report。',
'请查找错误日志的输出入口。',
'请定位异常打印的 console 源码。'
]
FILES['src/InvoiceExporter.ets']=FILES['src/InvoiceExporter.ets'].replace('exportInvoice','writeFile')
FILES['src/PaletteParser.ets']=FILES['src/PaletteParser.ets'].replace('parseColor','convertValue')
FILES['src/RuntimeLogger.ets']=FILES['src/RuntimeLogger.ets'].replace('RuntimeLogger','ErrorConsoleSink').replace('report(message','writeWarning(message')
FILES['src/ErrorConsoleSink.ets']=FILES.pop('src/RuntimeLogger.ets')
QUERIES[2]='请定位 palette 颜色转换的源码实现。'
QUERIES[3]='请查找 palette 颜色转换的源码实现。'
QUERIES[5]='请定位 ErrorConsoleSink.writeWarning。'
if __name__=='__main__':
 label=sys.argv[1];project=ROOT/'competition-fixture';project.mkdir(exist_ok=True)
 for name,source in FILES.items():
  p=project/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(source)
 (ROOT/'competition-protocol.json').write_text(json.dumps({'classification':'independent Development','sources':FILES,'queries':QUERIES,'expected':['src/InvoiceExporter.ets']*2+['src/PaletteParser.ets']*2+['src/ErrorConsoleSink.ets']*4},ensure_ascii=False,indent=2))
 def call(*args):
  cmd=[sys.executable,str(REPO/'tools/agent_memory.py'),*args,'--project',str(project),'--memory-home',str(ROOT/(label+'-memory'))]
  p=subprocess.run(cmd,cwd=REPO,text=True,capture_output=True);assert p.returncode==0,p.stderr
  return {'command':cmd,'stdout':p.stdout}
 setup=[call('init'),call('learn-path','--path','.')];rows=[]
 for i,query in enumerate(QUERIES):
  for compact in (False,True):
   row=call('context','--query',query,'--json',*(['--compact'] if compact else []));row.update(index=i,compact=compact);rows.append(row)
   print(i,compact,[(a['file_path'],a.get('symbol')) for a in json.loads(row['stdout'])['query_handoff']['code_anchors']],flush=True)
 (ROOT/(label+'.json')).write_text(json.dumps(rows,ensure_ascii=False,indent=2))
