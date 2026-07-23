@Component
export struct FilterToggle {
  @Prop denseMode: boolean = false

  build() {
    Button(this.denseMode ? 'Compact' : 'Comfortable')
      .height(this.denseMode ? 32 : 48)
      .padding({ left: 12, right: 12 })
  }
}
