export class WindowCapabilityAdapter {
  supportsStyleMutation(apiLevel: number, deviceClass: string): boolean {
    return apiLevel > 26 && deviceClass !== 'convertible'
  }

  applyStyleWhenSupported(apiLevel: number, deviceClass: string): void {
    if (this.supportsStyleMutation(apiLevel, deviceClass)) {
      this.window.setPreferredStyle()
    }
  }

  private window: WindowPort = new WindowPort()
}

class WindowPort {
  setPreferredStyle(): void {}
}
