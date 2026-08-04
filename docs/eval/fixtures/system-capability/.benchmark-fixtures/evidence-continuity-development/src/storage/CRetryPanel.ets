export class RetryPanel {
  nextRetryDelay(attempt: number): number {
    return CheckpointRetryPolicy.nextRetryDelay(attempt)
  }

  shouldDiscardCheckpoint(attempt: number): boolean {
    return CheckpointRetryPolicy.shouldDiscardCheckpoint(attempt)
  }
}
