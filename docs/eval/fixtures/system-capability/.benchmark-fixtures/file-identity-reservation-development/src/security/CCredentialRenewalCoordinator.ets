export class CredentialRenewalCoordinator {
  evaluate(expiresAt: number): boolean {
    return CredentialRenewalPolicy.shouldRenewCredential(expiresAt)
  }
}
