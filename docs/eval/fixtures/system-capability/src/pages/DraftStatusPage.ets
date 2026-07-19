@Component
export struct DraftStatusPage {
  @State checkpointStatus: string = 'incremental checkpoint pending'

  build() {
    Column() {
      Text(this.checkpointStatus)
      Text('Final draft save status')
    }
  }
}
