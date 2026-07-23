@Component
export struct KeyboardFocusHint {
  @State focusMessage: string = 'Editor focus unavailable'

  updateFocusMessage(value: string): void {
    this.focusMessage = value
  }
}
