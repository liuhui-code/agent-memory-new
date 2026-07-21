interface MediaCleanupLease {
  destroy(): void
}

export class LeaseController {
  private lease?: MediaCleanupLease

  attach(lease: MediaCleanupLease): void {
    this.lease = lease
  }

  releaseLease(): void {
    if (this.lease === undefined) {
      return
    }
    this.lease.destroy()
    this.lease = undefined
  }
}
