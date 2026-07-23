@Component
export struct EditorKeyboardPage {
  aboutToAppear(): void {
    this.windowStage.on('keyboardHeightChange', () => {})
  }

  build() {
    Text('Editor keyboard diagnostics')
  }
}
