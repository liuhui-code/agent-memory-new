export class DesktopEditorFocusController {
  private editorFocusable: boolean = true

  attach(stage: WindowStage): void {
    stage.on('keyboardHeightChange', (height: number) => {
      if (height > 0) {
        this.editorFocusable = true
      } else {
        this.editorFocusable = false
      }
    })
  }
}
