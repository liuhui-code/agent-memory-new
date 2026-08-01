export class DeferredSizePolicy {
  resolve(assetWidth: number, assetHeight: number): MeasureResult {
    const width = Math.max(1, assetWidth)
    const height = Math.max(1, assetHeight)
    return {
      width,
      height,
      mode: MeasureMode.DEFERRED
    }
  }
}
