export class DocumentLoader {
  async loadEntry(entry: number): Promise<string> {
    return await this.remote.read(entry)
  }
}
