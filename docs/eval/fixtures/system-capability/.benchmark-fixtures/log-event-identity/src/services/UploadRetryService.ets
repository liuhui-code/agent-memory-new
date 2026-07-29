import { EventLogger as eventLogger } from '../logging/EventLogger'

const TAG = 'UploadRetry'

export class UploadRetryService {
  retry(error: Error): void {
    eventLogger.warn(TAG, `UPLOAD_EVENT_913B transfer retry failed: ${error.message}`)
  }
}
