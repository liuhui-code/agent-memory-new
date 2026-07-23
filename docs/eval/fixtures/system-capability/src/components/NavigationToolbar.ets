@Component
export struct NavigationToolbar {
  @Builder
  buildToolbar() {
    Row() {
      Button('Back')
      Text('Workspace')
    }
    .height(56)
    .width('100%')
  }

  build() {
    this.buildToolbar()
  }
}
