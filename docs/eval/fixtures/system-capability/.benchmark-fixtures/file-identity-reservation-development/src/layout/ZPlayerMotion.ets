export class FullPlayerPagerSpec {
  static paneCount(width: number, height: number): number {
    return width > height ? 2 : 1
  }
}
