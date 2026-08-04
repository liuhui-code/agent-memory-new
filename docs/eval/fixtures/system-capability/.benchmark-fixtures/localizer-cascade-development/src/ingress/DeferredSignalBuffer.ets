export class DeferredSignalBuffer {
  private pendingSignal: string = ''

  preserveBeforeReady(signal: string): void {
    this.pendingSignal = signal
  }

  consumeWhenAttached(): string {
    const signal = this.pendingSignal
    this.pendingSignal = ''
    return signal
  }
}
