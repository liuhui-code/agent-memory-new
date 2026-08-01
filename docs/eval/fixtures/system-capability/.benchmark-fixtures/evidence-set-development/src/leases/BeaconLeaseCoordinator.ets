export class BeaconLeaseCoordinator {
  acquireExclusiveBeaconLease(nodeId: string): string {
    return `beacon-lease:${nodeId}`
  }
}
