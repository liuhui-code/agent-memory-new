export interface ScheduledWork {
  deadline: number
  insertionSequence: number
}

export class StableSchedule {
  orderReadyWork(ready: ScheduledWork[]): ScheduledWork[] {
    return ready.sort((left, right) => {
      if (left.deadline !== right.deadline) {
        return left.deadline - right.deadline
      }
      return left.insertionSequence - right.insertionSequence
    })
  }
}
