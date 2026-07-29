export class ReaderSettingsBridge {
  static async hydrateReadingScale(): Promise<void> {
    const storedScale = await LocalSettings.getString('reader_scale')
    if (storedScale === '') {
      return
    }
    ReaderDisplay.setScale(Number(storedScale))
  }
}
