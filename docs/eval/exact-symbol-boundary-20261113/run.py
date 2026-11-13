# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json, subprocess, sys, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent/'builder-owner-investigation'
FILES={'StripPanel.ets': '@Component\nstruct StripPanel {\n  build() {\n    Column() {\n      this.renderStrip()\n    }\n  }\n  @Builder\n  renderStrip() {\n    List() {\n      ForEach(this.tiles, (tile: Tile) => {\n        ListItem() { TileView({ tile: tile }) }\n      })\n    }\n    .listDirection(Axis.Horizontal)\n    .height(180)\n  }\n}\n', 'TileView.ets': '@Component\nstruct TileView {\n  build() {\n    Column() { Text(this.title) }\n    .height(70)\n  }\n}\n', 'StripModel.ets': 'export class StripModel {\n  getTiles(): Tile[] {\n    return this.tiles\n  }\n}\n', 'SplitPanel.ets': "@Component\nstruct SplitPanel {\n  @Builder\n  renderDirection() {\n    List() { Text('direction') }\n    .listDirection(Axis.Horizontal)\n  }\n  @Builder\n  renderSize() {\n    List() { Text('size') }\n    .height(180)\n  }\n}\n"}
QUERIES=['A horizontal media list clips tiles in its viewport. Locate the Builder method that owns list direction and height.', 'Tiles are cut off in a horizontally scrolling strip; return the reusable list Builder rather than a tile or data model.', '横向媒体列表中的方块被裁剪，请返回设置列表方向和高度的 Builder 源码，不要返回方块或数据模型。', 'Locate TileView.build source.', 'Locate StripModel.getTiles source.', 'Locate SplitPanel.renderDirection source.']
if __name__=='__main__':
 label=sys.argv[1]
 for suffix in ('.ets',):
  path=ROOT/('fixture'+suffix);path.mkdir(exist_ok=True)
  files={str(Path(k).with_suffix(suffix)):v for k,v in FILES.items()}
  for k,v in files.items():(path/k).write_text(v)
  def call(*args):
   cmd=[sys.executable,str(REPO/'tools/agent_memory.py'),*args,'--project',str(path),'--memory-home',str(ROOT/(label+'-memory'+suffix))]
   r=subprocess.run(cmd,cwd=REPO,text=True,capture_output=True)
   return dict(command=cmd,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr)
  frozen={'revision':subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD']).decode().strip(),'files':files,'queries':QUERIES,'expected':['StripPanel']*3+['TileView','StripModel','SplitPanel']}
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
