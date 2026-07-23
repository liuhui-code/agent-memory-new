@Component
export struct InventoryList {
  @State rows: string[] = []

  build() {
    List() {
      ForEach(this.rows, (row: string) => {
        ListItem() {
          Text(row)
        }
      })
    }
    .divider({ strokeWidth: 1, color: Color.Gray })
  }
}
