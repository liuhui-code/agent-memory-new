export class CounterPanelViewModel {
  private sharedCounter: SharedCounter = getSharedCounter()

  addOne(): void {
    this.sharedCounter.increment()
  }
}
