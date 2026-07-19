export class OrderActionButton {
  submit(order: OrderDraft): void {
    this.dispatchCommit(order)
  }

  private dispatchCommit(order: OrderDraft): void {}
}
