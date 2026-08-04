export class CheckpointReporter {
  discardCheckpoint(): void {
    CheckpointTransaction.discardCheckpoint()
    this.lastReport = ''
  }

  private lastReport: string = ''
}
