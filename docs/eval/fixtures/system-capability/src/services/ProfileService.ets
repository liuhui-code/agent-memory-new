import hilog from '@ohos.hilog'

export class ProfileService {
  loadProfile(): void {
    hilog.error(0x1000, 'ProfileService', 'profile load failed session invalid')
  }
}
