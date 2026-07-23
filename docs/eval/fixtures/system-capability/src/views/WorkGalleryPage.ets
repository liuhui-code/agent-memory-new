@Entry
@Component
struct WorkGalleryPage {
  build() {
    Column() {
      this.renderHeader()
      this.renderWorkGallery()
    }
  }

  @Builder
  renderWorkGallery() {
    List() {
      ForEach(this.works, (item: Work) => {
        ListItem() { WorkCard({ item: item }) }
      })
    }
    .listDirection(Axis.Horizontal)
    .height(160)
  }
}
