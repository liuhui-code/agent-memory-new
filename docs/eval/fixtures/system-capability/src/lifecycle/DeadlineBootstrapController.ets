export class DeadlineBootstrapController {
  private cancelled: boolean = false
  private ready: boolean = false

  async startWithDeadline(): Promise<void> {
    this.cancelled = false
    const deadline = new Promise<void>((resolve) => {
      setTimeout(() => {
        this.cancelled = true
        resolve()
      }, 3000)
    })
    await Promise.race([this.initializeWorkspace(), deadline])
  }

  private async initializeWorkspace(): Promise<void> {
    await this.loadAccount()
    if (this.cancelled) {
      return
    }
    await this.loadWorkspace()
    if (this.cancelled) {
      return
    }
    this.ready = true
  }

  private async loadAccount(): Promise<void> {}

  private async loadWorkspace(): Promise<void> {}
}
