// Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

@Entry
@Component
struct PreferenceDialogPage {
  @State detailVisible: boolean = true

  confirmClose(): void {
    this.detailVisible = false
  }

  build() {
    Button('Close details').onClick(() => {
      this.confirmClose()
    })
  }
}
