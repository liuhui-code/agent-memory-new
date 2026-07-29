export class RefreshCoordinator {
  private refreshTimer?: number

  scheduleRefresh(): void {
    if (this.refreshTimer !== undefined) {
      return
    }
    this.refreshTimer = setInterval(() => {
      this.publishLatestSnapshot()
    }, 1_000)
  }

  private publishLatestSnapshot(): void {
    SnapshotStore.updateCurrent()
  }
}
