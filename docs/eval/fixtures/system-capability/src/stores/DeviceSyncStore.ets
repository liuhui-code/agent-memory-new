export class DeviceSyncStore {
  @State devices: DeviceCard[] = []
  private repository: DeviceRepository

  async syncFromCompanion(): Promise<void> {
    const latest = await this.repository.loadDevices()
    this.devices = latest
  }
}
