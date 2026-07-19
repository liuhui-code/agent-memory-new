export default class WorkspaceAbility {
  private callback: WindowCallback = new WindowCallback()

  onWindowStageDestroy(): void {
    this.windowRegistry.unregisterWindowCallback(this.callback)
  }
}
