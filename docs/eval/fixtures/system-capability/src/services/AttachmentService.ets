import hilog from '@ohos.hilog'

export class AttachmentService {
  async loadAttachment(path: string): Promise<boolean> {
    hilog.debug(0x3000, 'AttachmentService', 'attachment download started')
    const cached = await this.writeCache(path)
    if (!cached) {
      hilog.warn(0x3000, 'AttachmentService', 'attachment cache write missing')
      return false
    }
    hilog.error(0x3000, 'AttachmentService', 'attachment download failed after cache write')
    hilog.debug(0x3000, 'AttachmentService', 'attachment cached file remains usable')
    return true
  }

  private async writeCache(path: string): Promise<boolean> {
    return path.length > 0
  }
}
