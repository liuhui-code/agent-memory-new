export class SyncFlushService {
  flushPendingSync(batchId: string): void {
    SyncWriter.flush(batchId)
  }
}
