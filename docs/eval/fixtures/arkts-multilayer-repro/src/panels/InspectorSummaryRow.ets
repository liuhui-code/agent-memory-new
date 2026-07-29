@Component
export struct InspectorSummaryRow {
  @Prop title: string

  build() {
    Row() {
      Text(this.title)
    }
    .onClick(() => Logger.info('inspector summary selected'))
  }
}
