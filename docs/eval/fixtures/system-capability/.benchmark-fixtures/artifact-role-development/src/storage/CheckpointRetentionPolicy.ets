export class CheckpointRetentionPolicy {
  finalizeCheckpoint(checkpointId: string): void {
    this.committedCheckpoint = checkpointId
    this.stagedCheckpoint = ''
  }

  discardCheckpoint(): void {
    this.stagedCheckpoint = ''
  }

  private stagedCheckpoint: string = ''
  private committedCheckpoint: string = ''
}
