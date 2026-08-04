export class CheckpointTransaction {
  discardCheckpoint(): void {
    this.stagedCheckpoint = ''
  }

  private stagedCheckpoint: string = ''
}
