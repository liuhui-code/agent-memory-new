export interface WorkspaceRow {
  id: string
  schema: string
}

export class WorkspaceSelectionController {
  @State selectedId: string = ''
  @State selectedSchema: string = ''

  onEditRequested(row: WorkspaceRow): void {
    this.selectedId = row.id
    this.selectedSchema = row.schema
    this.openEditPanel()
  }

  private openEditPanel(): void {}
}
