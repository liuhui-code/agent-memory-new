export class CipherRotationCoordinator {
  rotateActiveCipher(keyAlias: string): string {
    return `rotated:${keyAlias}`
  }
}
