@Component
export struct JobDispatchButton {
  @Prop label: string = 'Run job'

  build() {
    Button(this.label)
  }
}
