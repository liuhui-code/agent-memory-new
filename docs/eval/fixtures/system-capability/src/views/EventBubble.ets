interface TimelineEntry {
  id: number
  category: string
  text: string
}

@Component
export struct EventBubble {
  @Prop entry: TimelineEntry
  @Prop showHeader: boolean = true

  build() {
    Column() {
      if (this.showHeader) {
        Text(this.entry.category)
      }
      Text(this.entry.text)
    }
  }
}
