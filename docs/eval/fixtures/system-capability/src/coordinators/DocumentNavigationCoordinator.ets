export class DocumentNavigationCoordinator {
  private requestedEntry: number = 0
  private visibleContent: string = ''

  async warmIndex(): Promise<void> {
    await this.loader.prepare()
  }

  updateLabel(label: string): void {
    this.label = label
  }

  resetIndicator(): void {
    this.loading = false
  }

  async navigateToEntry(entry: number): Promise<void> {
    this.requestedEntry = entry
    const content = await this.loader.load(entry)
    if (entry !== this.requestedEntry) {
      return
    }
    this.visibleContent = content
  }
}
