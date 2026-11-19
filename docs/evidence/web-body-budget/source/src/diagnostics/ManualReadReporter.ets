import hilog from '@ohos.hilog'

export class ManualReadReporter {
  note(message: string): void {
    hilog.info(42, 'ManualIndexer', '%{public}s', message)
  }
}
