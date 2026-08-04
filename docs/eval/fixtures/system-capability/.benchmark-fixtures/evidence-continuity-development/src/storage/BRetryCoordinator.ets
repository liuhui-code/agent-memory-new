export class RetryCoordinator {
  scheduleNextRetryDelay(attempt: number): number {
    return CheckpointRetryPolicy.nextRetryDelay(attempt)
  }

  evaluateDiscardCheckpoint(attempt: number): boolean {
    return CheckpointRetryPolicy.shouldDiscardCheckpoint(attempt)
  }
}
