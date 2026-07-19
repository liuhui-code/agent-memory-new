export class OrderValidator {
  validate(order: OrderDraft): boolean {
    if (order.customerId.trim().length === 0) {
      console.error('Required customer')
      return false
    }
    return true
  }
}
