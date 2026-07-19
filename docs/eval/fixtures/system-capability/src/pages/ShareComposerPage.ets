@Component
export struct ShareComposerPage {
  @State sharedRecords: ShareRecord[] = []

  build() {
    Text(`Shared records: ${this.sharedRecords.length}`)
  }
}
