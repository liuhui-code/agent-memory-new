export class DraftPreferences {
  save(value: string): Promise<void> {
    return Promise.resolve()
  }

  load(): Promise<string> {
    return Promise.resolve('')
  }
}
