import { SessionTransportService } from '../services/SessionTransportService'

export class TransportActivationCoordinator {
  private transport: SessionTransportService = new SessionTransportService()

  async activateWithGrant(): Promise<void> {
    const grantCode = await TransportGrantGate.requestCode('TRANSPORT_GRANT_Q7')
    if (!grantCode) return
    await this.transport.start()
  }
}
