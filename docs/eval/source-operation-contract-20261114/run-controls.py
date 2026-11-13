# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,sys,subprocess,os
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO=Path(os.environ.get('RUNTIME_REPO',ROOT.parent/'capability-owner-investigation'))
FILES={
'src/runtime/ExtensionInspector.ets':'''import { bundleManager } from '@kit.AbilityKit'
export class ExtensionInspector {
  async inspectInstalled(): Promise<boolean> {
    const details = await bundleManager.getBundleInfoForSelf(0)
    return details.extensionAbilityInfo.length > 0
  }
}
''',
'src/config/ExtensionManifest.ets':'''export const ExtensionManifest = {
  capability: 'Runtime capability unavailable',
  declaredExtension: 'Share',
  probeRequired: true,
}
''',
'src/ui/ExtensionSettings.ets':'''@Component
struct ExtensionSettings {
  build() {
    Column() {
      Text('Runtime capability inspection unavailable')
      Text('Bundle extension capability query settings')
    }
  }
}
''',
'src/runtime/ProbeNotes.ets':'''export class ProbeNotes {
  explain(): string {
    return 'bundleManager.getBundleInfoForSelf(0) runtime capability'
  }
}
'''}
QUERIES=[
'The manifest declares a capability but runtime inspection rejects it. Locate executable runtime capability probing source.',
'Find the bundle capability query that checks an installed extension, not the settings text.',
'运行时扩展能力检查不可用，请定位执行 bundle 能力探测的方法，不要返回设置页面。',
'Locate ExtensionSettings.build source.',
'Locate ExtensionInspector.inspectInstalled and ExtensionSettings.build source.'
]
QUERIES += [
'Find runtime capability text.',
'Find runtime capability manifest metadata.',
'Locate the literal `runtime capability` in ProbeNotes.explain.',
'Find runtime capability source and declaration.',
'Compare the runtime capability checks in the installed extension inspector and the spare extension inspector.'
]
FILES['src/runtime/SpareExtensionInspector.ets'] = FILES['src/runtime/ExtensionInspector.ets'].replace('ExtensionInspector','SpareExtensionInspector')
if __name__=='__main__':
 label=sys.argv[1];root=ROOT/'controls-fixture';root.mkdir(exist_ok=True)
 for k,v in FILES.items():
  p=root/k;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(v)
 (ROOT/'controls-protocol.json').write_text(json.dumps({'files':FILES,'queries':QUERIES,'expected_primary':'src/runtime/ExtensionInspector.ets','controls':'explicit settings and two targets preserved'},indent=2,ensure_ascii=False))
 def call(*args):
  cmd=[sys.executable,str(REPO/'tools/agent_memory.py'),*args,'--project',str(root),'--memory-home',str(ROOT/(label+'-memory'))]
  r=subprocess.run(cmd,cwd=REPO,text=True,capture_output=True);return {'command':cmd,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
 setup=[call('init'),call('learn-path','--path','.')];assert all(r['returncode']==0 for r in setup),setup
 outputs=[]
 for i,q in enumerate(QUERIES):
  for compact in (False,True):
   r=call('context','--query',q,'--json',*(['--compact'] if compact else []));r.update(index=i,compact=compact);outputs.append(r)
   print(i,compact,[a['file_path'] for a in json.loads(r['stdout'])['query_handoff']['code_anchors']],flush=True)
 (ROOT/(label+'.json')).write_text(json.dumps(outputs,indent=2,ensure_ascii=False))
