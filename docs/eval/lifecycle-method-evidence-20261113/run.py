# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json, subprocess, sys, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent/'lifecycle-owner-investigation'
FILES={
'PanelAbility.ets':'''export class PanelAbility {
  onWindowStageDestroy(): void {
    this.listeners.unregisterViewCallback(this.callback)
  }
}
''',
'PanelWidget.ets':'''export class PanelWidget {
  onWindowStageDestroy(): void {
    this.visible = false
  }
}
''',
'CallbackRegistry.ets':'''export class CallbackRegistry {
  removeCallback(): void {
    this.listeners.unregisterViewCallback(this.callback)
  }
}
''',
'SplitAbility.ets':'''export class SplitAbility {
  onWindowStageDestroy(): void {
    this.visible = false
  }
  releaseCallback(): void {
    this.listeners.unregisterViewCallback(this.callback)
  }
}
'''
}
QUERIES=[
'A listener must be unregistered before the panel context is destroyed. Locate the lifecycle cleanup owner.',
'Panel shutdown leaves a callback registered; return the ability that owns both destruction and callback cleanup.',
'面板上下文销毁前没有注销监听回调，请只返回同时拥有生命周期边界和清理动作的源码。',
'Locate PanelWidget.onWindowStageDestroy source.',
'Locate CallbackRegistry.removeCallback source.',
'Locate SplitAbility.releaseCallback source.'
]
if __name__=='__main__':
 label=sys.argv[1]
 for suffix in ('.ets','.ts'):
  path=ROOT/('fixture'+suffix);path.mkdir(exist_ok=True)
  files={str(Path(k).with_suffix(suffix)):v for k,v in FILES.items()}
  for k,v in files.items():(path/k).write_text(v)
  def call(*args):
   cmd=[sys.executable,str(REPO/'tools/agent_memory.py'),*args,'--project',str(path),'--memory-home',str(ROOT/(label+'-memory'+suffix))]
   r=subprocess.run(cmd,cwd=REPO,text=True,capture_output=True)
   return dict(command=cmd,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr)
  frozen={'revision':subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD']).decode().strip(),'files':files,'queries':QUERIES,'expected':['PanelAbility']*3+['PanelWidget','CallbackRegistry','SplitAbility']}
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
