export class ExampleQuotaPolicy {
  showQuotaExample(bytes: number): boolean {
    return bytes <= 8
  }
}
