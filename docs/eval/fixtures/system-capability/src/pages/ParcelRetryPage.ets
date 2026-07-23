@Entry
@Component
struct ParcelRetryPage {
  @State retryPending: boolean = false
  @State failureMessage: string = ''

  private async retryFailedParcel(): Promise<void> {
    if (this.retryPending) {
      return
    }
    this.retryPending = true
    try {
      await ParcelDeliveryService.retryFailedParcel()
      this.failureMessage = ''
    } catch (error) {
      this.failureMessage = 'parcel retry failed'
    } finally {
      this.retryPending = false
    }
  }

  build() {
    Button('Retry parcel')
      .enabled(!this.retryPending)
      .onClick(() => {
        this.retryFailedParcel()
      })
    Text(this.failureMessage)
  }
}
