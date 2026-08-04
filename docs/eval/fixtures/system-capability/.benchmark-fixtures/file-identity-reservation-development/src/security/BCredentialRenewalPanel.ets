export class CredentialRenewalPanel {
  update(expiresAt: number): boolean {
    return CredentialRenewalPolicy.shouldRenewCredential(expiresAt)
  }
}
