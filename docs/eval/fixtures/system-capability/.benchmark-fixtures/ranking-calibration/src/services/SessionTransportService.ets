export class SessionTransportService {
  async start(): Promise<void> {
    await NativeTransport.openSession()
  }
}
