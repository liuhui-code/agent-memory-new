export class SessionCodeGenerator {
  generateSessionCode(secret: string): string {
    return secret.slice(0, 6)
  }
}
