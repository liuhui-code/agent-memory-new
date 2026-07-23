@Component
export struct PasteImportPage {
  @State clipboardText: string = ''

  build() {
    Column() {
      Text('Clipboard plain text import')
      Text(this.clipboardText)
    }
  }
}
