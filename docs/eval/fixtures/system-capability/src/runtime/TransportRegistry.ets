export class TransportRegistry {
  private repository: DeviceRepository = new RemoteDeviceRepository()

  selectRepository(online: boolean): void {
    if (online) {
      this.repository = new RemoteDeviceRepository()
    } else {
      this.repository = new DemoDeviceRepository()
    }
  }
}
