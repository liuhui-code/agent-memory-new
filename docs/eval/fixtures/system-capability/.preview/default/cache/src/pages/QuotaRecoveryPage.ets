@Entry
@Component
struct QuotaRecoveryPage {
  @State retryEnabled: boolean = false
  @State recoveryNotice: string = ''

  private applyQuotaRecovery(): void {
    this.retryEnabled = true
    this.recoveryNotice = 'quota recovery ready'
  }

  build() {
    Button('Recover quota')
      .onClick(() => {
        this.applyQuotaRecovery()
      })
    Text(this.recoveryNotice)
  }
}
