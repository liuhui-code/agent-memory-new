export class ProfileDraftViewModel {
  private draftName: string = ''
  private store: DraftStore = new DraftStore()

  updateDraftName(value: string): void {
    this.draftName = value
  }

  async commitDraft(): Promise<void> {
    const name = this.draftName.trim()
    if (name === '') {
      return
    }
    await this.store.saveDraft(name)
  }
}
