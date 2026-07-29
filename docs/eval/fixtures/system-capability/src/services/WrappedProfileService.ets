import { DomainLogger } from '../logging/DomainLogger'

export class WrappedProfileService {
  private logger: DomainLogger = new DomainLogger()

  load(): void {
    this.logger.report('WRAP_PROFILE_7F19 load failed')
  }
}
