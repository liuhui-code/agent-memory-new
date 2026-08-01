@Component
struct AlertSurface {
  @State hasBlockingError: boolean = false

  @Styles warningSurface() {
    .backgroundColor(this.hasBlockingError ? Color.Red : Color.Transparent)
    .borderWidth(this.hasBlockingError ? 2 : 0)
  }

  private updateBlockingError(active: boolean): void {
    this.hasBlockingError = active
  }

  build() {
    Column() {
      Text('operation status')
        .warningSurface()
    }
  }
}
