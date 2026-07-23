@Component
export struct RuleCreatorPage {
  @State private detailsExpanded: boolean = false

  @Builder
  private DetailsDisclosure() {
    Row() {
      Text('Rule details')
      SymbolGlyph($r('sys.symbol.chevron_down'))
        .rotate({ angle: this.detailsExpanded ? 180 : 0 })
    }.onClick(() => {
      this.detailsExpanded = !this.detailsExpanded
    })
  }

  build() {
    this.DetailsDisclosure()
  }
}
