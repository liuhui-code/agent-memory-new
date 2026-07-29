// Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

@Entry
@Component
struct CollectionWorkspacePage {
  @State activeSection: string = 'saved'

  build() {
    Column() {
      Button('Saved').onClick(() => this.showSaved())
      Button('Recent').onClick(() => this.showRecent())
      this.renderSection()
    }
  }

  showSaved(): void {
    this.activeSection = 'saved'
  }

  showRecent(): void {
    this.activeSection = 'recent'
  }

  @Builder
  renderSection() {
    if (this.activeSection === 'saved') {
      Text('Saved collection')
    } else {
      Text('Recent collection')
    }
  }
}
