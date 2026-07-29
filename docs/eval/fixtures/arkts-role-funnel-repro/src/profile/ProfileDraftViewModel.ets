export class ProfileDraftViewModel {
  private draftName: string = ''
  private store: DraftStore = new DraftStore()

  async commitDraft(): Promise<void> {
    const name = this.draftName.trim()
    if (name === '') {
      return
    }
    await this.store.saveDraft(name)
  }
}
