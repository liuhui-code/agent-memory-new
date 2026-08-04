export class CredentialRenewalPolicy {
  static shouldRenewCredential(expiresAt: number): boolean {
    return expiresAt <= Date.now()
  }
}
