export class DeliveryRetryCoordinator {
  private retryHandle?: number

  startRetryCycle(): void {
    if (this.retryHandle !== undefined) {
      return
    }
    this.retryHandle = setInterval(() => {
      this.publishDeliveryState()
    }, 1_000)
  }

  private publishDeliveryState(): void {
    DeliveryState.markWaiting()
  }
}
