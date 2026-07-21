export class SnapshotTransferAbility {
  async createSnapshotArchive(): Promise<void> {
    await this.persistTransferState('create')
  }

  async restoreSnapshotArchive(): Promise<void> {
    await this.persistTransferState('restore')
  }

  private async persistTransferState(_mode: string): Promise<void> {}
}
