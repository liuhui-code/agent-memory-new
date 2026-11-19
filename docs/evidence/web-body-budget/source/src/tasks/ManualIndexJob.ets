import { ManualReadReporter } from '../diagnostics/ManualReadReporter'

export class ManualIndexJob {
  private reporter: ManualReadReporter

  constructor(reporter: ManualReadReporter) {
    this.reporter = reporter
  }

  refresh(): void {
    this.reporter.note('WebView URL navigation policy index reload complete')
  }
}
