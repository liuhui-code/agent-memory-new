export class TelemetrySocketGateway {
  private client: TelemetrySocket

  async attach(): Promise<void> {
    this.client.onPayload((raw: string) => {
      const event = JSON.parse(raw)
      this.accept(event)
    })
  }

  private accept(event: TelemetryEvent): void {
    this.events.push(event)
  }
}
