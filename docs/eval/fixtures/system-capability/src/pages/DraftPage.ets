@Entry
@Component
export struct DraftPage {
  @State draftText: string = ''

  aboutToAppear(): void {
    this.reloadPreview()
  }

  reloadPreview(): void {
    this.draftText = ''
  }

  build() {}
}
