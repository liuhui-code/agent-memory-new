export class PreviewSessionCoordinator {
  private generation: number = 0
  private controller?: PreviewController

  async startPreview(assetId: string): Promise<void> {
    const generation = ++this.generation
    const controller = await PreviewController.create(assetId)
    if (generation != this.generation) {
      controller.dispose()
      return
    }
    this.controller = controller
  }

  replacePreview(assetId: string): void {
    this.stopPreview()
    void this.startPreview(assetId)
  }

  stopPreview(): void {
    this.generation++
    this.controller?.dispose()
    this.controller = undefined
  }
}
