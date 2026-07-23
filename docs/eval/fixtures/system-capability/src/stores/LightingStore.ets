export class LightingStore {
  @State current: LightState = new LightState()
  private repository: LightingRepository

  async runCommand(command: LightCommand): Promise<void> {
    await this.repository.executeAction(command)
  }

  async refreshState(): Promise<void> {
    const latest = await this.repository.loadCurrent()
    this.current = latest
  }
}
