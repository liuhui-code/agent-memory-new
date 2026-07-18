import { TimelineRow } from '../views/TimelineRow'

interface TimelineEntry {
  id: number
  category: string
  text: string
}

@Entry
@Component
struct TimelinePage {
  @State entries: TimelineEntry[] = []

  private shouldShowHeader(entry: TimelineEntry, index: number): boolean {
    if (index === 0) {
      return true
    }
    return this.entries[index - 1].category !== entry.category
  }

  build() {
    List() {
      ForEach(this.entries, (entry: TimelineEntry, index: number) => {
        ListItem() {
          TimelineRow({
            entry: entry,
            showHeader: this.shouldShowHeader(entry, index)
          })
        }
      })
    }
  }
}
