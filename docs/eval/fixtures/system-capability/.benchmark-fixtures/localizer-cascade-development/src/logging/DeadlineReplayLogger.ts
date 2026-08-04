export class DeadlineReplayLogger {
  logQueueOrder(earliestDeadline: number, insertionSequence: number): void {
    console.info(`ready work ${earliestDeadline} ${insertionSequence}`)
  }
}
