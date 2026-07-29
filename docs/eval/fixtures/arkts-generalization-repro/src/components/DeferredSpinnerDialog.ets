// Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

@CustomDialog
export struct DeferredSpinnerDialog {
  @State rotateAngle: number = 0

  aboutToAppear(): void {
    setTimeout(() => {
      this.rotateAngle = 360
    }, 80)
  }

  build() {
    Image($r('app.media.spinner'))
      .rotate({ angle: this.rotateAngle })
      .animation({ duration: 1200, iterations: -1 })
  }
}
