export class CapabilityReader {
  private available: boolean = false

  resolve(): boolean {
    this.available = canIUse('SystemCapability.ArkUI.ArkUI.Full')
    return this.available
  }



  label(): string {
    return this.available ? 'available' : 'unavailable'
  }
}
