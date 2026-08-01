import { ViewportTelemetry } from '../logging/ViewportTelemetry'

@Component
export struct ViewportHost {
  @State contentWidth: number = 0

  build(): void {
    Row() {
      Text(`${this.contentWidth}`)
    }
    .onAreaChange((_oldArea: Area, newArea: Area) => {
      this.contentWidth = Number(newArea.width)
      ViewportTelemetry.notice(this.contentWidth)
    })
  }
}
