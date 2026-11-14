export class SampleLedger {
  private accepted: number[] = [];
  recordSuccessfulSample(value: number): void {
    this.accepted.push(value);
  }
  latestSample(): number {
    return this.accepted[this.accepted.length - 1];
  }
}
