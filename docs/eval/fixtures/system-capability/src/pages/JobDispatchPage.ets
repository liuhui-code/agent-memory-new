@Component
export struct JobDispatchPage {
  private transport: JobTransport = new JobTransport()

  @Builder
  private DispatchButton() {
    Button('Run job').onClick(async () => {
      const result = await this.transport.submit('nightly')
      if (typeof result === 'boolean') {
        this.showBanner('Job submitted')
      } else {
        this.showBanner(`Job failed: ${result}`)
      }
    })
  }

  private showBanner(_message: string): void {}

  build() {
    this.DispatchButton()
  }
}
