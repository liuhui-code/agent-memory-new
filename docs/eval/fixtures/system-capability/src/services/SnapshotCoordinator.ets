export class SnapshotCoordinator {
  private preferences: Preferences

  async restoreSnapshot(payload: string, maximumBytes: number): Promise<void> {
    if (payload.length > maximumBytes) {
      return
    }
    const saved = await this.preferences.get('snapshot_key')
    this.controller.restore(saved)
  }
}
