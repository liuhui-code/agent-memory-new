@Component
export struct SeatCell {
  @State selected: boolean = false

  onCellTapped(): void {
    this.selected = !this.selected
  }

  build() {}
}
