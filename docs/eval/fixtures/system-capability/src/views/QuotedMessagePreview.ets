@Component
export struct QuotedMessagePreview {
  @Prop text: string = ''

  build() {
    Row() {
      Text(this.text)
        .fontSize(12)
        .maxLines(1)
    }
    .width('100%')
  }
}
