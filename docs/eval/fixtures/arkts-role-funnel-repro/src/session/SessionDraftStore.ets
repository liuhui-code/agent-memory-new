export class SessionDraftStore {
  private latestId: string = ''

  async saveLatest(id: string): Promise<void> {
    if (id === '') {
      return
    }
    this.latestId = id
    await Preferences.put('latest-session', id)
  }
}
