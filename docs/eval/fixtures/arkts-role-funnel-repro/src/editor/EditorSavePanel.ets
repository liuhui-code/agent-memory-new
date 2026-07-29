@Component
export struct EditorSavePanel {
  @State subject: string = ''

  private async applySubject(): Promise<void> {
    const value = this.subject.trim()
    if (value === '') {
      return
    }
    await DraftStore.saveSubject(value)
  }

  build() {
    Button('Save').onClick(() => this.applySubject())
  }
}
