export interface CachedResult {
  updatedAt: number
  value: string
}

export class BoundedResultCache {
  private entries: Map<string, CachedResult> = new Map()

  constructor(private capacity: number) {}

  put(key: string, value: string): void {
    this.entries.set(key, { updatedAt: Date.now(), value: value })
    if (this.entries.size <= this.capacity) {
      return
    }
    let oldestKey: string | undefined = undefined
    let oldestTime: number = Number.MAX_SAFE_INTEGER
    for (const [candidateKey, candidate] of this.entries) {
      if (candidate.updatedAt < oldestTime) {
        oldestTime = candidate.updatedAt
        oldestKey = candidateKey
      }
    }
    if (oldestKey !== undefined) {
      this.entries.delete(oldestKey)
    }
  }
}
