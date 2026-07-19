export interface DraftRepository {
  saveDraft(sessionId: string, content: string): Promise<void>
}

export class ConversationDraftStore {
  private writeTail: Promise<void> = Promise.resolve()

  constructor(private repository: DraftRepository) {}

  normalizeContent(content: string): string {
    return content.trim()
  }

  measureContent(content: string): number {
    return content.length
  }

  shouldCheckpoint(content: string): boolean {
    return content.length > 0
  }

  queueIncrementalWrite(sessionId: string, content: string): void {
    const snapshot = this.normalizeContent(content)
    this.writeTail = this.writeTail.then(async () => {
      await this.repository.saveDraft(sessionId, snapshot)
    })
  }

  describePendingWrite(): string {
    return 'incremental draft checkpoint pending'
  }

  formatCompletion(content: string): string {
    return this.normalizeContent(content)
  }

  async commitCompletedDraft(sessionId: string, content: string): Promise<void> {
    await this.writeTail
    const completed = this.formatCompletion(content)
    await this.repository.saveDraft(sessionId, completed)
  }
}
