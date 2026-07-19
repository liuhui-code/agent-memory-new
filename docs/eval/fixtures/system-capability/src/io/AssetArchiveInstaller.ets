import fs from '@ohos.file.fs'

export class AssetArchiveInstaller {
  async installBundle(context: UIContext): Promise<void> {
    const data = context.resourceManager.getRawFileContentSync('bundle.zip')
    const archivePath = context.tempDir + '/bundle.zip'
    const archive = fs.openSync(archivePath, fs.OpenMode.CREATE)
    fs.writeSync(archive.fd, data.buffer)
    fs.closeSync(archive)
    await unzip(archivePath, context.filesDir)
  }
}
