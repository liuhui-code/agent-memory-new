export class ArchiveService {
  async apply(): Promise<void> {
    const value = await this.preferences.get('theme_font_payload_v7')
    await this.archive.write(value)
  }
}
