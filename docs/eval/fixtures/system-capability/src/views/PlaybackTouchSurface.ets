@Entry
@Component
struct PlaybackTouchSurface {
  @State lastX: number = 0

  build() {
    Stack() {}
      .onTouch((event: TouchEvent) => {
        const firstPointer = event.touches[0]
        this.lastX = firstPointer.x
      })
  }
}
