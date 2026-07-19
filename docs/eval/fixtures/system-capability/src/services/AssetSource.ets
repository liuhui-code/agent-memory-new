export class AssetSource {
  async getAssets(folderId: string): Promise<AssetItem[]> {
    return await this.mediaLibrary.queryAssets(folderId)
  }
}
