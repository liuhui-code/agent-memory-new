export class CheckpointTransaction {
  private staged?: CheckpointRecord

  stageCheckpoint(record: CheckpointRecord): void {
    this.validateCheckpoint(record)
    this.staged = record
  }

  async commitCheckpoint(): Promise<void> {
    const current = this.staged
    if (current == undefined) {
      return
    }
    try {
      await CheckpointStore.write(current)
      this.staged = undefined
    } catch (error) {
      this.rollbackCheckpoint()
      throw error
    }
  }

  rollbackCheckpoint(): void {
    this.staged = undefined
  }

  private validateCheckpoint(record: CheckpointRecord): void {
    if (record.revision <= 0) {
      throw new Error('invalid checkpoint revision')
    }
  }
}
