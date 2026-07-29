import { FailureReporter } from '../logging/FailureReporter'

export class DispatchProfileService {
  private reporter: FailureReporter

  constructor(reporter: FailureReporter) {
    this.reporter = reporter
  }

  run(): void {
    this.reporter.report('DISPATCH_PROFILE_8A21 load failed')
  }
}
