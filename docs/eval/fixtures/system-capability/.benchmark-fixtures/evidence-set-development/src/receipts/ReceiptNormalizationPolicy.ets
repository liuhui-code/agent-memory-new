export class ReceiptNormalizationPolicy {
  normalizeCurrency(receipt: string): string {
    return receipt.replace('RMB', 'CNY')
  }
}
