export class DocumentSession {
  private ready: boolean = false
  private documentPath: string = ''
  constructor(private reader: DocumentReader) {}
  async swapDocument(path: string): Promise<void> {
    this.ready = false
    this.documentPath = path
    await this.reader.openDocument(path)
  }
}
export class DocumentReader {
  async openDocument(path: string): Promise<void> {
    await fetch(path)
  }
}
