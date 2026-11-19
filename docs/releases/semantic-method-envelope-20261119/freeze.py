from pathlib import Path
import json,hashlib
O=Path(__file__).resolve().parent
cases=[]
for domain,record,store in [('Voucher','VoucherRecord','VoucherStore'),('Lease','LeaseRecord','LeaseStore')]:
 source=f'''export interface {record} {{
  usageCount: number
  lastUsedAt: number
}}

export class {domain}UsageCoordinator {{
  private store: {store} = new {store}()

  async recordSuccessfulUse(record: {record}): Promise<void> {{
    record.usageCount += 1
    record.lastUsedAt = Date.now()
    await this.store.save(record)
  }}
}}
'''
 cases.append(dict(id=domain,sources={domain+'UsageCoordinator.ets':source},queries=[dict(id='persistence',query=f'Return the {domain.lower()} usage counter and timestamp persistence coordinator.'),dict(id='named',query=f'Locate {domain}UsageCoordinator.recordSuccessfulUse source.'),dict(id='declaration',query=f'Locate the {record} entity definition.')]))
p=dict(classification='authored independent Development, static requests not reported incidents',stop='Freeze once. Only actual public missing method signature with existing body supports change; no fixture/query rewriting after results.',cases=cases)
s=json.dumps(p,ensure_ascii=False,indent=2);(O/'protocol.json').write_text(s);(O/'protocol.sha256').write_text(hashlib.sha256(s.encode()).hexdigest()+'\n')
