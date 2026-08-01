@Entry
@Component
struct WorkspaceShell {
  @State activeDocument: string = ''
  @State retainedDocument: string = ''

  @Builder renderActiveDocument() {
    Column() {
      Text(this.retainedDocument)
    }
  }

  private retainDocumentState(nextDocument: string): void {
    if (this.activeDocument !== nextDocument) {
      this.retainedDocument = this.activeDocument
      this.activeDocument = nextDocument
    }
  }

  build() {
    Stack() {
      this.renderActiveDocument()
    }
  }
}
