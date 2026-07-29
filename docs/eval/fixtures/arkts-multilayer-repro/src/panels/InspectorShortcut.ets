@Component
export struct InspectorShortcut {
  @Prop itemId: string

  build() {
    Button('Inspect')
      .onClick(() => {
        if (PanelRouter.isOpen('inspector', this.itemId)) {
          PanelRouter.focus('inspector', this.itemId)
          return
        }
        PanelRouter.open('inspector', this.itemId)
      })
  }
}
