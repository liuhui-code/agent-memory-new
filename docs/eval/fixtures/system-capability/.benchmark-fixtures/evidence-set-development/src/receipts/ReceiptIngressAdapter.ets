export class ReceiptIngressAdapter {
  decodeEnvelope(payload: string): string {
    return payload.trim()
  }
}
