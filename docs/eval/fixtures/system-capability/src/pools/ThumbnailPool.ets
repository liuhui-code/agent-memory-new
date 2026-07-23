export class ThumbnailPool {
  private thumbnails: Map<string, string> = new Map()

  constructor(private capacity: number) {}

  storeThumbnail(key: string, payload: string): void {
    this.thumbnails.set(key, payload)
    if (this.thumbnails.size <= this.capacity) {
      return
    }
    const oldestKey = this.thumbnails.keys().next().value
    this.thumbnails.delete(oldestKey)
  }
}
