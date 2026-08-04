export class DeadlineReplayMetrics {
  recordStableInsertionSequence(deadline: number): void {
    console.info(`ready work earliest deadline ${deadline} insertion sequence`)
  }
}
