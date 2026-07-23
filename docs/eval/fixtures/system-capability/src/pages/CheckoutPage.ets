import { PaymentService } from '../services/PaymentService'

@Component
struct CheckoutPage {
  private paymentService: PaymentService = new PaymentService()

  submitOrder(): void {
    this.paymentService.chargeOrder()
  }

  build() {}
}
