import { PassageLogger as archiveLogger } from '../logging/PassageLogger'

const TAG = 'ArchiveRestore'

export class ArchiveRestoreService {
  validateRequest(archiveId: string): boolean {
    return archiveId.length > 0
  }

  loadManifest(archiveId: string): Promise<string> {
    return Promise.resolve(archiveId)
  }

  decodeManifest(manifest: string): string {
    return manifest.trim()
  }

  verifyChecksum(manifest: string): boolean {
    return manifest.length > 4
  }

  reserveTarget(archiveId: string): string {
    return `/restore/${archiveId}`
  }

  releaseTarget(target: string): void {
    target.length
  }

  reportProgress(archiveId: string): void {
    archiveId.length
  }

  finishRestore(archiveId: string): void {
    archiveId.length
  }

  restoreArchive(archiveId: string): Promise<void> {
    const target = this.reserveTarget(archiveId)
    return this.loadManifest(archiveId)
      .then((manifest: string) => {
        if (!this.verifyChecksum(this.decodeManifest(manifest))) {
          throw new Error('checksum mismatch')
        }
        this.reportProgress(archiveId)
      })
      .catch((error: Error) => {
        archiveLogger.error(
          TAG,
          `ARCHIVE_EVENT_D42A restore rejected: ${error.message}; archive=${archiveId}`
        )
        this.releaseTarget(target)
      })
  }
}
