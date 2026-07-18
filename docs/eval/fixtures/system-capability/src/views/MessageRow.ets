import { QuotedMessagePreview } from './QuotedMessagePreview'

@Component
export struct MessageRow {
  @Prop messageText: string = ''
  @Prop quotedText: string = ''

  build() {
    Column() {
      Text(this.messageText)
        .fontSize(16)
      if (this.quotedText.length > 0) {
        QuotedMessagePreview({ text: this.quotedText })
      }
    }
  }
}
