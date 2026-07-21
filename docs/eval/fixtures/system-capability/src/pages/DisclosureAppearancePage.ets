@Component
export struct DisclosureAppearancePage {
  @State private symbolSize: number = 18

  build() {
    Column() {
      Text('Disclosure appearance')
      Slider({ value: this.symbolSize, min: 12, max: 32 })
    }
  }
}
