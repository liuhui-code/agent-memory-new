import hilog from '@ohos.hilog'
import { FailureReporter } from './FailureReporter'

export class FileFailureReporter implements FailureReporter {
  report(message: string): void {
    hilog.error(0x3201, 'FileFailureReporter', message)
  }
}
