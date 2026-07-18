import hilog from '@ohos.hilog'

export class PaymentService {
  chargeOrder(): void {
    hilog.error(0x2000, 'PaymentService', 'payment duplicate order rejected')
  }
}
