export class CanvasSelection {
  private selectedHandle: number = -1

  selectHandle(handle: number): void {
    this.selectedHandle = handle
  }
}
