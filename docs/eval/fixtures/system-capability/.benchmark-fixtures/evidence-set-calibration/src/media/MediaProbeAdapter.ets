export class MediaProbeAdapter {
  readNativeDuration(handle: number): number {
    return NativeMedia.duration(handle)
  }
}
