import hilog from '@ohos.hilog'
import { FailureReporter } from './FailureReporter'

export class ConsoleFailureReporter implements FailureReporter {
  report(message: string): void {
    hilog.error(0x3200, 'ConsoleFailureReporter', message)
  }
}
