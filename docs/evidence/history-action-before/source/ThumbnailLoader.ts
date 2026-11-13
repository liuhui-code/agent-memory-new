export class ThumbnailLoader {
  async load(path: string): Promise<void> {
    try {
      await fetch(path)
    } catch (error) {
      console.error('THUMBNAIL_READ_FAILED: load failed')
    }
  }
}
