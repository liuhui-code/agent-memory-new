export class CheckpointPreview {
  discardCheckpoint(): void {
    CheckpointTransaction.discardCheckpoint()
    this.preview = ''
  }

  private preview: string = ''
}
