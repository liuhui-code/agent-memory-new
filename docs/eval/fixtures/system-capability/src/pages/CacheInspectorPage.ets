@Component
export struct CacheInspectorPage {
  @State oldestEntryLabel: string = 'Oldest cached result'

  build() {
    Column() {
      Text(this.oldestEntryLabel)
      Text('Entry limit and eviction status')
    }
  }
}
