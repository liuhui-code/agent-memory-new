export class InfoSheetCoordinator {
  public requestOpen(): void {
    this.presentInfoSheet()
  }

  public completeClose(): void {
    this.releaseInfoSheet()
  }

  private presentInfoSheet(): void {}
  private releaseInfoSheet(): void {}
}
