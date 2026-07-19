export class WindowRegistry {
  unregisterWindowCallback(callback: WindowCallback): void {
    this.callbacks.delete(callback)
  }
}
