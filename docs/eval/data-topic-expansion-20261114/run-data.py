# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,subprocess,sys,os
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO=Path(os.environ.get('RUNTIME_REPO',ROOT.parent/'color-owner-investigation'))
FILES={
'src/ClipboardReader.ets':'export class ClipboardReader {\n  readContent(): string {\n    return pasteboard.getSystemPasteboard().getData().getPrimaryText()\n  }\n}\n',
'src/PaletteConverter.ets':'export class PaletteConverter {\n  convertValue(value: string): number {\n    return Number.parseInt(value, 16)\n  }\n}\n',
'src/ProfileService.ets':"export class ProfileService {\n  fetchUser(): string {\n    console.info('load request network profile account user data')\n    return network.fetch('/user/profile')\n  }\n}\n"}
QUERIES=['请返回读取 clipboard 剪贴板数据的实现。','请返回读取 clipboard 剪贴板内容的实现。','请返回 palette 数据转换实现。','请返回 palette 内容转换实现。','请返回加载用户资料的网络实现。','请返回 ProfileService.fetchUser。']
if __name__=='__main__':
 label=sys.argv[1];project=ROOT/'data-fixture';project.mkdir(exist_ok=True)
 for name,source in FILES.items():
  p=project/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(source)
 (ROOT/'data-protocol.json').write_text(json.dumps({'classification':'independent Development','sources':FILES,'queries':QUERIES,'expected':['src/ClipboardReader.ets']*2+['src/PaletteConverter.ets']*2+['src/ProfileService.ets']*2},ensure_ascii=False,indent=2))
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
