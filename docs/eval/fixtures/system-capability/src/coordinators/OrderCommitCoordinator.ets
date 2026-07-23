export interface OrderDraft {
  customerId: string
}

export class OrderCommitCoordinator {
  private orderStore: OrderStore = new OrderStore()

  async commitOrder(order: OrderDraft): Promise<void> {
    if (order.customerId.trim().length === 0) {
      promptAction.showToast({ message: 'Required customer' })
      return
    }
    this.dispatchCommit(order)
    await this.orderStore.save(order)
  }

  private dispatchCommit(order: OrderDraft): void {}
}
