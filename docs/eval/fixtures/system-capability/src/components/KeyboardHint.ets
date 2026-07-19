@Component
export struct KeyboardHint {
  private event: KeyEvent

  build() {
    Text(`Key: ${this.event.keyCode}`)
  }
}
