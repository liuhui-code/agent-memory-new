@Component
export struct TouchOverlay {
  build() {
    Stack() {}
      .onTouch((_event: TouchEvent) => {
        this.showOverlay()
      })
  }
}
