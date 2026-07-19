@Entry
@Component
struct WorkspacePage {
  aboutToDisappear(): void {
    this.flushViewState()
  }

  build() {
    Column() {}
  }
}
