@Component
export struct RuleEditorPage {
  @State private detailsExpanded: boolean = false

  @Builder
  private DetailsDisclosure() {
    Column() {
      Row() {
        Text('Rule details')
        SymbolGlyph($r('sys.symbol.chevron_down'))
          .rotate({ angle: this.detailsExpanded ? 0 : 180 })
      }
      .onClick(() => {
        this.detailsExpanded = !this.detailsExpanded
      })

      if (this.detailsExpanded) {
        Text('Advanced matching options')
      }
    }
  }

  build() {
    this.DetailsDisclosure()
  }
}
