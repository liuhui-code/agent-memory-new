@Component
export struct RecordPreview {
  @Prop sharedRecord: ShareRecord

  build() {
    Text(this.sharedRecord.content)
  }
}
