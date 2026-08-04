export class ResponsivePaneHost {
  paneCount(width: number, height: number): number {
    return FullPlayerPagerSpec.paneCount(width, height)
  }
}
