from pathlib import Path
import json,subprocess
O=Path(__file__).resolve().parent;R=O.parent/'repo';refs=['da9f504']+subprocess.check_output(['git','rev-list','--reverse','--first-parent','da9f504..5cd6183','--','tools'],cwd=R,text=True).splitlines();lo=0;hi=len(refs)-1;results=[]
def check(ref):
 p=O/('version-'+ref)/'compact.stdout'
 if not p.exists():
  r=subprocess.run(['python','-B',str(O/'version-probe.py'),ref],capture_output=True,text=True);assert r.returncode==0,r.stderr
 x=json.loads(p.read_text());paths=[a['file_path']for a in x['query_handoff']['code_anchors']];bad=paths!=['src/web/DesktopEditorFocusController.ets'];results.append(dict(ref=ref,bad=bad,paths=paths));print(results[-1],flush=True);return bad
assert not check(refs[lo]);assert check(refs[hi])
while hi-lo>1:
 mid=(lo+hi)//2
 if check(refs[mid]):hi=mid
 else:lo=mid
(O/'transition.json').write_text(json.dumps(dict(scope='binary-searched adjacent runtime revision transition; does not establish monotonic behavior across every historical commit',good=refs[lo],bad=refs[hi],runs=results),indent=2));print('TRANSITION',refs[lo],refs[hi],flush=True)
