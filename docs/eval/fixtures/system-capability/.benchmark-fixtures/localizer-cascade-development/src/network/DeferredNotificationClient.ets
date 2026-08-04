export class DeferredNotificationClient {
  requestDeferredActivation(pendingSignal: string): void {
    Network.send(`buffer before ready and activate after surface attaches ${pendingSignal}`)
  }
}
