# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
import json,hashlib
from pathlib import Path
D=Path(__file__).resolve().parent
sources={
 'SyncMenu.ets':"""@Component
export struct SyncMenu {
  private actions = [
    {
      caption: 'Restart sync',
      run: () => {
        this.worker.stopSync()
      }
    },
    {
      caption: 'Stop sync',
      run: () => {
        this.worker.stopSync()
      }
    }
  ]
  build() { Column() {} }
}
""",
 'SyncWorker.ets':"""export class SyncWorker {
  restartSync(): void {
    this.transport.startSync()
  }
  stopSync(): void {
    this.transport.stopSync()
  }
}
""",
 'CommandOutput.ets':"""@Component
export struct CommandOutput {
  build() { Text('Restart sync command output') }
}
"""}
p={'classification':'independent Development, new redo not restoration','sources':sources,
 'queries':[{'query':'Choosing Restart sync starts shutdown instead of restarting. Locate the menu command binding owner, not transport infrastructure or its row view.','expected':['SyncMenu.ets']},
 {'query':'Locate the menu command binding owner for Stop sync.','expected':['SyncMenu.ets']}],
 'negative_contracts':['duplicate matching owner: unchanged','label in adjacent object without callback: unchanged','unknown template interpolation or slash: unchanged','stale digest: unchanged','missing/duplicate callback identity: unchanged','copy/serialize/mutated receipt: unchanged','path/log obligations: unchanged','incomplete snapshot/1500 budget: unchanged'],
 'hashes':{n:hashlib.sha256(s.encode()).hexdigest()for n,s in sources.items()}}
(D/'protocol.json').write_text(json.dumps(p,indent=2))
