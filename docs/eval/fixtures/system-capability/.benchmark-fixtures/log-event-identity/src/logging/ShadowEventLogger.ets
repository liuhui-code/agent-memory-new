import hilog from '@ohos.hilog'

export class EventLogger {
  static warn(tag: string, format: string, ...args: string[]): void {
    hilog.warn(0x3201, tag, format, args)
  }

  static info(tag: string, format: string, ...args: string[]): void {
    hilog.info(0x3201, tag, format, args)
  }
}
