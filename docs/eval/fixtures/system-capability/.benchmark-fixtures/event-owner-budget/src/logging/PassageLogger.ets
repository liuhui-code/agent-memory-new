import hilog from '@ohos.hilog'

export class PassageLogger {
  static error(tag: string, format: string, ...args: string[]): void {
    hilog.error(0x4200, tag, format, args)
  }
}
