@Component
export struct CanvasPreview {
  @State visible: boolean = false

  build(): void {
    Column() {
      Canvas(this.renderContext)
    }
    .visibility(this.visible ? Visibility.Visible : Visibility.Hidden)
  }
}
