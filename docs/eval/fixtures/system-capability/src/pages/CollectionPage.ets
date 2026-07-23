@Entry
@Component
struct CollectionPage {
  @State folderId: string = ''

  updateFolder(folderId: string): void {
    if (folderId.length > 0) {
      this.folderId = folderId
    }
  }

  build() {
    Column() {}
  }
}
