export class ConnectionRecoveryPolicy {
  shouldResume(previousRoute: string, currentRoute: string): boolean {
    return previousRoute.length > 0 && previousRoute !== currentRoute
  }

  recordSuccessfulResume(routeId: string): void {
    this.lastResumedRoute = routeId
  }

  private lastResumedRoute: string = ''
}
