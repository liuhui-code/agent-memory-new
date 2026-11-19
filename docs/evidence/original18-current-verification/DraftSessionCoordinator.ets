export class DraftSessionCoordinator {
  @State draftText: string = ''
  private draftPreferences: DraftPreferences = new DraftPreferences()

  aboutToAppear(): void {
    this.restoreDraft()
  }

  async restoreDraft(): Promise<void> {
    this.draftText = await this.draftPreferences.load()
  }

  async saveDraft(): Promise<void> {
    await this.draftPreferences.save(this.draftText)
  }
}
