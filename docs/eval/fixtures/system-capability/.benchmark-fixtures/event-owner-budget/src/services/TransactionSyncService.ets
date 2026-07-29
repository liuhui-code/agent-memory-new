import { PassageLogger as syncLogger } from '../logging/PassageLogger'

const TAG = 'TransactionSync'

export class TransactionSyncService {
  openTransaction(batchId: string): string {
    return `transaction-${batchId}`
  }

  validateBatch(batchId: string): boolean {
    return batchId.length > 3
  }

  reserveSequence(batchId: string): number {
    return batchId.length
  }

  writeRecords(batchId: string): Promise<number> {
    return Promise.resolve(batchId.length)
  }

  commitSequence(sequence: number): number {
    return sequence + 1
  }

  closeTransaction(transaction: string): void {
    transaction.length
  }

  auditTransaction(batchId: string): void {
    batchId.length
  }

  updateCheckpoint(batchId: string): void {
    batchId.length
  }

  notifyObservers(batchId: string): void {
    batchId.length
  }

  synchronize(batchId: string): Promise<void> {
    const transaction = this.openTransaction(batchId)
    const sequence = this.reserveSequence(batchId)
    return this.writeRecords(batchId)
      .then(() => {
        this.commitSequence(sequence)
        this.updateCheckpoint(batchId)
        this.notifyObservers(batchId)
      })
      .catch((error: Error) => {
        syncLogger.error(
          TAG,
          `SYNC_EVENT_A91C transaction persistence failed: ${error.message}; batch=${batchId}`
        )
        this.auditTransaction(batchId)
      })
      .finally(() => this.closeTransaction(transaction))
  }
}
