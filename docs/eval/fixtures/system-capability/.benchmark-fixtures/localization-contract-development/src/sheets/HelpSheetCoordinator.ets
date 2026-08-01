export class HelpSheetCoordinator {
  public requestOpen(): void {
    this.presentHelpSheet()
  }

  public completeClose(): void {
    this.releaseHelpSheet()
  }

  private presentHelpSheet(): void {}
  private releaseHelpSheet(): void {}
}
