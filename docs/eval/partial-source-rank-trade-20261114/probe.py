# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,subprocess,sys,os
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO=Path(os.environ.get('RUNTIME_REPO',ROOT.parent/'partial-source-budget-investigation'))
FILES={'RefreshStore.ets': "export class RefreshStore {\n  private adapter: RefreshAdapter\n  private result: string = ''\n  async dispatch(command: string): Promise<void> {\n    await this.adapter.executeAction(command)\n  }\n  async refreshState(): Promise<void> {\n    const latest = await this.adapter.loadCurrent()\n    this.result = latest\n  }\n}\n", 'NoticeSink.ets': "export class NoticeSink {\n  report(command: string): void {\n    console.info('cached content remains usable after updating')\n  }\n  emit(): void {\n    console.info('network task finished with cached result')\n  }\n}\n", 'NoticeRelay.ets': 'export class NoticeRelay {\n  private logger: NoticeSink\n  notify(command: string): void {\n    this.logger.report(command)\n  }\n}\n'}
FILES.update({'CommitButton.ets': 'export class CommitButton {\n  dispatchCommit(value: string): void {\n    this.service.submit(value)\n  }\n}\n', 'GesturePanel.ets': 'export class GesturePanel {\n  onActionStart(): void {\n    this.active = true\n  }\n}\n'})
FILES['RefreshStore.ets']=FILES['RefreshStore.ets'].replace('  private adapter:', '  private pendingRefreshRevision: number = 0\n  private lastRefreshTimestamp: number = 0\n  private retryDelayMilliseconds: number = 1000\n  private maximumRefreshAttempts: number = 3\n  private successfulRefreshCount: number = 0\n  private adapter:')
FILES['RefreshStore.ets']=FILES['RefreshStore.ets'].replace('  private adapter:', ''.join('  private configurationValue'+str(i)+': number = 0\n' for i in range(16))+'  private adapter:')
QUERIES=['The action completes but state remains unchanged. Locate action dispatch and authoritative refresh ownership.']
project=ROOT/(sys.argv[1]+'-fixture');project.mkdir(exist_ok=True)
for name,source in FILES.items():(project/name).write_text(source)
(ROOT/'source-protocol.json').write_text(json.dumps({'classification':'independent Development','sources':FILES,'queries':QUERIES,'contract':'legacy inference retained; explicit overrides authoritative'},indent=2,ensure_ascii=False))
def run(*args):
 p=subprocess.run([sys.executable,str(REPO/'tools/agent_memory.py'),*args,'--project',str(project),'--memory-home',str(ROOT/(sys.argv[1]+'-memory'))],capture_output=True,text=True,cwd=REPO);assert p.returncode==0,p.stderr;return p.stdout
run('init');run('learn-path','--path','.')
rows=[]
for q in QUERIES:
 for compact in (False,True):
  payload=json.loads(run('context','--query',q,'--json',*(['--compact'] if compact else [])))
  rows.append({'query':q,'compact':compact,'payload':payload})
  print(compact,[(x['file_path'],[(y['start_line'],y['end_line'],y.get('truncated')) for y in x.get('source_excerpts',[])]) for x in payload['query_handoff']['code_anchors']],payload.get('output_budget'))
(ROOT/(sys.argv[1]+'.json')).write_text(json.dumps(rows,ensure_ascii=False,indent=2))
