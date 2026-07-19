export class DocumentSelectionStore {
  private selectedEntry: number = 0

  selectEntry(entry: number): void {
    this.selectedEntry = entry
  }
}
