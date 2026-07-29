import hilog from '@ohos.hilog'

export class LogSink {
  emit(message: string): void {
    hilog.error(0x3100, 'ProfileFlow', message)
  }
}
