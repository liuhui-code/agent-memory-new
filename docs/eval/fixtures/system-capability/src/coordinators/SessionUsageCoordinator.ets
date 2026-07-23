export interface SessionRecord {
  usageCount: number
  lastUsedAt: number
}

export class SessionUsageCoordinator {
  private sessionStore: SessionStore = new SessionStore()

  async recordSuccessfulUse(session: SessionRecord): Promise<void> {
    session.usageCount += 1
    session.lastUsedAt = Date.now()
    await this.sessionStore.save(session)
  }
}
