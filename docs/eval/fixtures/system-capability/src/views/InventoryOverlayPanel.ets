@Component
export struct InventoryOverlayPanel {
  @State selectedCategory: number = 0

  build() {
    Column() {
      Grid() {
        GridItem() { Text('Category chooser') }
      }
      Row() {
        TextInput({ placeholder: 'Numeric quantity' })
      }
      .shadow({ radius: 12 })
      .backgroundColor(Color.White)
    }
  }
}
