export class EditorResultViewModel {
  private title: string = ''
  private note: string = ''

  submitAndReturn(): void {
    const result = { title: this.title.trim(), note: this.note.trim() }
    ResultNavigator.returnWithResult(result)
  }
}
