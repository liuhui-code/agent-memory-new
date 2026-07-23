@Component
export struct CommandOutputPage {
  @State output: string = ''

  build() {
    Column() {
      Text('Command output')
      Text(this.output || 'Empty output')
    }
  }
}
