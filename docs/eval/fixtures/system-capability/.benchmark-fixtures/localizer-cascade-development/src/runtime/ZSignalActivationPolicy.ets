import { DeferredSignalBuffer } from '../ingress/DeferredSignalBuffer'

export class SignalActivationPolicy {
  activateAfterSurfaceAttach(buffer: DeferredSignalBuffer): void {
    const pendingSignal = buffer.consumeWhenAttached()
    if (pendingSignal.length > 0) {
      NotificationRuntime.activate(pendingSignal)
    }
  }
}
