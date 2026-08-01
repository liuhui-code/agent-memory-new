import { SyncFlushService } from './SyncFlushService'

@Component
export struct SyncStatusPanel {
  private service: SyncFlushService = new SyncFlushService()

  onFlushRequested(batchId: string): void {
    this.service.flushPendingSync(batchId)
  }
}
