@Component
export struct UpgradeStatusPage {
  @State archiveStatus: string = 'Preparing asset extraction'

  build() {
    Text(this.archiveStatus)
  }
}
