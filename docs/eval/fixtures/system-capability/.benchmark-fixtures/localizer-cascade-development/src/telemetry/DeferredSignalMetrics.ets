export class DeferredSignalMetrics {
  recordSurfaceAttach(pendingSignal: string): void {
    console.info(`surface attaches consume pending signal ${pendingSignal}`)
  }
}
