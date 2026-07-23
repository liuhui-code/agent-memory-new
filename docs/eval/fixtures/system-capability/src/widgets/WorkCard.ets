@Component
export struct WorkCard {
  @Prop item: Work

  build() {
    Column() { Text(this.item.title) }
      .height(160)
      .padding(8)
  }
}
