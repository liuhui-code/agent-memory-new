@Component
export struct NotificationRow {
  @Prop title: string = ''

  build() {
    Row() {
      Text(this.title)
        .layoutWeight(1)
      Image($r('app.media.chevron'))
    }
    .margin({ left: 4, right: 12 })
    .padding({ top: 6, bottom: 6 })
  }
}
