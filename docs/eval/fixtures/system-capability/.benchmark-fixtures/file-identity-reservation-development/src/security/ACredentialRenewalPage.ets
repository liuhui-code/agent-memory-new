export class CredentialRenewalPage {
  refresh(expiresAt: number): boolean {
    return CredentialRenewalPolicy.shouldRenewCredential(expiresAt)
  }
}
