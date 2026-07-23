import { SnapshotCoordinator } from '../services/SnapshotCoordinator'

@Component
struct SnapshotAuditPage {
  private coordinator: SnapshotCoordinator = new SnapshotCoordinator()

  async refreshSnapshot(): Promise<void> {
    await this.coordinator.restoreSnapshot('', 1024)
  }

  build(): void {
    Button('Restore').onClick(() => this.refreshSnapshot())
  }
}
