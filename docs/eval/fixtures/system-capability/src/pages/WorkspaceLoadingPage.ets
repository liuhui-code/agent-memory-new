@Component
export struct WorkspaceLoadingPage {
  @State timeoutMessage: string = 'Initialization deadline exceeded'

  build() {
    Column() {
      Text(this.timeoutMessage)
      Text('Background setup status')
    }
  }
}
