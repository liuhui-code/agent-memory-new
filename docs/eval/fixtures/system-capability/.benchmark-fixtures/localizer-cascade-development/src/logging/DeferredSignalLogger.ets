export class DeferredSignalLogger {
  logPendingLifecycle(signal: string): void {
    console.info(`deferred notification pending signal preserve consume ${signal}`)
  }
}
