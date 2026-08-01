import { hilog as systemLog } from '@kit.PerformanceAnalysisKit'

export class ViewportTelemetry {
  static notice(width: number): void {
    systemLog.info(
      0x3100,
      'ViewportHost',
      'VIEWPORT_EVENT_E73B width changed',
      width
    )
  }
}
