export class ReceiptExportCoordinator {
  async exportForHarmonyScreen(receiptId: string): Promise<string> {
    const target = getContext(this).filesDir
    return `\${target}/\${receiptId}.json`
  }
}
