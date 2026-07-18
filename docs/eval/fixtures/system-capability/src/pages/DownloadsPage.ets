import { AttachmentService } from '../services/AttachmentService'

@Component
struct DownloadsPage {
  private service: AttachmentService = new AttachmentService()

  async retryDownload(path: string): Promise<void> {
    await this.service.loadAttachment(path)
  }

  build() {}
}
