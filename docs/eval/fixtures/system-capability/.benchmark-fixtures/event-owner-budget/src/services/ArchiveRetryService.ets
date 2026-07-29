import { PassageLogger as archiveLogger } from '../logging/PassageLogger'

const TAG = 'ArchiveRetry'

export class ArchiveRetryService {
  scheduleRetry(error: Error, archiveId: string): void {
    archiveLogger.error(
      TAG,
      `ARCHIVE_EVENT_D42B restore retry deferred: ${error.message}; archive=${archiveId}`
    )
  }
}
