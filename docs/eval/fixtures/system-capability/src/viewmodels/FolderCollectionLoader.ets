export class FolderCollectionLoader {
  @State items: AssetItem[] = []
  private assetSource: AssetSource = new AssetSource()

  async loadFolder(folderId: string): Promise<void> {
    if (folderId.length > 0) {
      this.items = await this.assetSource.getAssets(folderId)
    }
  }
}
