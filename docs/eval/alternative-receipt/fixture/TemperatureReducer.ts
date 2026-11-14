export class TemperatureReducer {
  reduce(readings: number[]): number {
    let latest = 0;
    for (const reading of readings) {
      if (Number.isFinite(reading)) {
        latest = reading;
      } else {
        latest = 0;
      }
    }
    return latest;
  }
}
