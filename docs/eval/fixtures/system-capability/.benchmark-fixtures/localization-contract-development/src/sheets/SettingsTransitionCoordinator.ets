export class SettingsTransitionCoordinator {
  private closing: boolean = false
  private pendingReopen: boolean = false

  public requestOpen(): void {
    if (this.closing) {
      this.pendingReopen = true
      return
    }
    this.presentSettingsSheet()
  }

  public completeClose(): void {
    this.closing = false
    if (this.pendingReopen) {
      this.pendingReopen = false
      this.presentSettingsSheet()
    }
  }

  private presentSettingsSheet(): void {}
}
