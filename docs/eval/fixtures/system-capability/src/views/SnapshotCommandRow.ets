@Component
export struct SnapshotCommandRow {
  @Prop title: string
  @Event invoke: () => Promise<void>

  build() {
    Row() {
      Text(this.title)
      SymbolGlyph($r('sys.symbol.archivebox'))
    }.onClick(() => this.invoke())
  }
}
