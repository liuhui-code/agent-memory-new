export class WorkspaceSchema {
  id: string = ''
  selectedItem: string = ''

  describePreviousItem(): string {
    return `${this.id}:${this.selectedItem}`
  }
}
