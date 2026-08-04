export class DeadlineReplayClient {
  sendReadyWork(deadline: number, insertionSequence: number): void {
    Network.send({ deadline, insertionSequence, state: 'ready work' })
  }
}
