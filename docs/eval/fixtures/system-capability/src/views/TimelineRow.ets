import { EventBubble } from './EventBubble'

interface TimelineEntry {
  id: number
  category: string
  text: string
}

@Component
export struct TimelineRow {
  @Prop entry: TimelineEntry
  @Prop showHeader: boolean = true

  build() {
    EventBubble({
      entry: this.entry,
      showHeader: this.showHeader
    })
  }
}
