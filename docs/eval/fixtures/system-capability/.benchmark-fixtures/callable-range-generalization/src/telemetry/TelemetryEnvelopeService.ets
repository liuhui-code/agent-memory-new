export interface TelemetryNotice {
  channel: string
  payload: Object
}

export class TelemetryEnvelopeService {
  private static lastSequence: number = 0

  public static registerObserver(): void {
    console.info('telemetry observer registered')
  }

  private static async decodeWrappedSample(
    notice: TelemetryNotice,
    expectedChannel: string
  ): Promise<void> {
    if (notice.channel !== expectedChannel) {
      return
    }
    TelemetryEnvelopeService.lastSequence += 1
    console.info('wrapped telemetry sample decoded')
  }

  public static currentSequence(): number {
    return TelemetryEnvelopeService.lastSequence
  }
}
