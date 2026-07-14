export class ProfileService {
  load(): string {
    return this.normalize('Ada')
  }

  normalize(value: string): string {
    return value
  }
}
