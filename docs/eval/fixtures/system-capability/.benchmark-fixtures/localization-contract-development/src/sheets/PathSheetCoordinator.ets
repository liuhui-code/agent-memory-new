export class PathSheetCoordinator {
  public requestOpen(): void {
    this.presentPathSheet()
  }

  public completeClose(): void {
    this.releasePathSheet()
  }

  private presentPathSheet(): void {}
  private releasePathSheet(): void {}
}
