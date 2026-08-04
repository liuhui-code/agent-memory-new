export class CheckpointPanel {
  discardCheckpoint(): void {
    CheckpointTransaction.discardCheckpoint()
    this.visibleCheckpoint = ''
  }

  private visibleCheckpoint: string = ''
}
