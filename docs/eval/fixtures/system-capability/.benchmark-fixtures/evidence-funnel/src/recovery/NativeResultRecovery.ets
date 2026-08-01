export class NativeResultRecovery {
  retryFailedResult(): void {
    this.retryQueue.schedule('native result failure callback retry host')
  }
}
