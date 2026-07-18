import hilog from '@ohos.hilog'

export class NetworkClient {
  request(): void {
    hilog.error(0x3000, 'NetworkClient', 'generic network timeout')
  }
}
