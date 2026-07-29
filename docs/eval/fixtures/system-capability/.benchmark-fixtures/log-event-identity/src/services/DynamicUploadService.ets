import { EventLogger as eventLogger } from '../logging/EventLogger'

const TAG = 'DynamicUpload'

export class DynamicUploadService {
  upload(error: Error, sessionId: string): void {
    eventLogger.warn(
      TAG,
      `UPLOAD_EVENT_913A transfer failed: ${error.message}; session=${sessionId}`
    )
  }
}
