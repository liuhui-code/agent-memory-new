@Component
export struct WorkspaceSwitcher {
  @State currentWorkspace: string = 'overview'

  private activateWorkspace(nextWorkspace: string): void {
    if (this.currentWorkspace === nextWorkspace) {
      return
    }
    this.currentWorkspace = nextWorkspace
    WorkspaceStore.saveActive(nextWorkspace)
  }

  build() {
    Button('Open tasks')
      .onClick(() => this.activateWorkspace('tasks'))
  }
}
