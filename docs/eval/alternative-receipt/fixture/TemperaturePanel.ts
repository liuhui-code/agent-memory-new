import { TemperatureReducer } from './TemperatureReducer';
export class TemperaturePanel {
  private reducer = new TemperatureReducer();
  render(readings: number[]): string {
    const latest = this.reducer.reduce(readings);
    return String(latest);
  }
}
