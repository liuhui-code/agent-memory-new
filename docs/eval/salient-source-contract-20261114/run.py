import json, subprocess, sys, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent/'salient-contract-investigation'
FILES={'src/cache/IconStore.ets': 'export class IconStore {\n  private entries: Map<string, string> = new Map()\n  saveIcon(key: string, payload: string): void {\n    this.entries.set(key, payload)\n    if (this.entries.size > 8) {\n      const first = this.entries.keys().next().value\n      this.entries.delete(first)\n    }\n  }\n}\n', 'src/examples/IconStoreExample.ets': "import { IconStore } from '../cache/IconStore'\nexport function demonstrateIconStore(): void {\n  const store = new IconStore()\n  store.saveIcon('alpha', 'one')\n  store.saveIcon('beta', 'two')\n}\n", 'src/ui/RestoreView.ets': "@Component\nstruct RestoreView {\n  @State retryAllowed: boolean = false\n  @State statusMessage: string = ''\n  enableRecovery(): void {\n    this.retryAllowed = true\n    this.statusMessage = 'capacity recovery available'\n  }\n  build() {\n    Button('Restore capacity').onClick(() => this.enableRecovery())\n    Text(this.statusMessage)\n  }\n}\n", 'src/ui/RetryBadge.ets': "@Component\nstruct RetryBadge {\n  @State shown: boolean = false\n  build() {\n    Button('Retry status').onClick(() => this.shown = true)\n  }\n}\n", '.preview/cache/src/ui/RestoreView.ets': "@Component\nstruct RestoreView {\n  @State retryAllowed: boolean = false\n  @State statusMessage: string = ''\n  enableRecovery(): void {\n    this.retryAllowed = true\n    this.statusMessage = 'capacity recovery available'\n  }\n  build() {\n    Button('Restore capacity').onClick(() => this.enableRecovery())\n    Text(this.statusMessage)\n  }\n}\n"}
QUERIES=['The icon pool exceeds capacity. Locate the production implementation that deletes the oldest map key rather than its usage example.', 'Return executable icon eviction ownership: set the entry, inspect map size, take the first key, and delete it; exclude sample code.', '图标池超过容量后没有删除最早键，请返回检查 size、读取首个 key 并 delete 的正式实现，排除示例代码。', 'The capacity recovery button does not enable retry. Return the maintained source owner, not a generated preview copy.', 'Locate the canonical capacity recovery click handler that enables retry and updates the notice; exclude generated build artifacts.', 'capacity recovery 容量恢复按钮点击后没有启用重试，请返回正式源码中的状态更新，不要返回预览缓存生成物。', 'Locate demonstrateIconStore usage example source.', 'Locate RestoreView.enableRecovery source.']
FILES.update({
'src/cache/KeyCountProbe.ets': """export class KeyCountProbe {
  readSize(): number {
    return this.values.size
  }
}
""",
'src/services/NoticeService.ets': """export class NoticeService {
  updateNotice(): void {
    console.info('notice update dispatched')
  }
}
""",
'src/ui/NoticePreferences.ets': """import { NoticeService } from '../services/NoticeService'
export class NoticePreferences {
  service: NoticeService = new NoticeService()
  save(): void {
    this.service.updateNotice()
  }
}
"""
})
FILES.update({
'src/storage/LiteralCatalog.ets': """export function readArchiveDiagnostic(): string {
  return 'icon_archive_corrupt'
}
""",
'src/storage/KeyLabel.ets': """export function readKeyLabel(): string {
  return 'key'
}
"""
})
QUERIES.extend([
'Locate IconStore.saveIcon and KeyCountProbe.readSize source.',
'Return the production icon implementation that sets the entry, checks size and deletes the first key. Also locate `icon_archive_corrupt`.',
'Return the production icon implementation that checks size and deletes the first key. Also locate the literal `key`.',
'Locate the caller and emitter of the ordinary log message notice update dispatched.',
'Locate both the icon implementation and the key-count probe source.'
])
if __name__=='__main__':
 label=sys.argv[1]
 for suffix in ('.ets',):
  path=ROOT/('noise-fixture'+suffix);path.mkdir(exist_ok=True)
  files={str(Path(k).with_suffix(suffix)):v for k,v in FILES.items()}
  for k,v in files.items():
   (path/k).parent.mkdir(parents=True,exist_ok=True)
   (path/k).write_text(v)
  def call(*args):
   cmd=[sys.executable,str(REPO/'tools/agent_memory.py'),*args,'--project',str(path),'--memory-home',str(ROOT/(label+'-memory'+suffix))]
   r=subprocess.run(cmd,cwd=REPO,text=True,capture_output=True)
   return dict(command=cmd,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr)
  frozen={'revision':subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD']).decode().strip(),'files':files,'queries':QUERIES,'expected':['src/cache/IconStore.ets']*3+['src/ui/RestoreView.ets']*3+['src/examples/IconStoreExample.ets','src/ui/RestoreView.ets']}
  (ROOT/(label+'-frozen'+suffix+'.json')).write_text(json.dumps(frozen,indent=2,ensure_ascii=False))
  setup=[call('init'),call('learn-path','--path','.')]
  (ROOT/(label+'-setup'+suffix+'.json')).write_text(json.dumps(setup,indent=2))
  assert all(x['returncode']==0 for x in setup),setup
  outputs=[]
  for i,q in enumerate(QUERIES):
   for compact in (False,True):
    r=call('context','--query',q,'--json',*(['--compact'] if compact else []));r.update(index=i,compact=compact)
    outputs.append(r);(ROOT/(label+'-outputs'+suffix+'.json')).write_text(json.dumps(outputs,indent=2,ensure_ascii=False))
    if r['returncode']==0:print(suffix,i,compact,[a['file_path'] for a in json.loads(r['stdout'])['query_handoff']['code_anchors']],flush=True)
