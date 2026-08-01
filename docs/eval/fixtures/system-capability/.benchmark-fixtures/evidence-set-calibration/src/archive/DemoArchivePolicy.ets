export class DemoArchivePolicy {
  demonstrateArchiveRetention(days: number): boolean {
    return days <= 2
  }
}
