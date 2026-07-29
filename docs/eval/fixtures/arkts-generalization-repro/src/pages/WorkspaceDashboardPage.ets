// Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

@Entry
@Component
struct WorkspaceDashboardPage {
  @State activeSection: string = 'overview'
  @State selectedCollection: string = ''

  build() {
    Column() {
      Text(this.activeSection)
      this.buildHeader()
      this.buildBody()
    }
  }

  @Builder
  buildHeader() {
    Row() {
      Text('Workspace')
    }
  }

  @Builder
  buildBody() {
    Column() {
      Text(this.selectedCollection)
    }
  }

  openOverview(): void {
    this.activeSection = 'overview'
  }

  openArchive(): void {
    this.activeSection = 'archive'
  }

  selectCollectionForDisplay(collectionId: string): void {
    this.selectedCollection = collectionId
    this.activeSection = 'collection'
  }
}
