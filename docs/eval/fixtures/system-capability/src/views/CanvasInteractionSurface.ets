@Component
export struct CanvasInteractionSurface {
  @State activeHandle: number = -1

  build() {
    Stack() {
      Canvas()
    }
    .gesture(
      PanGesture()
        .onActionStart((event: GestureEvent) => {
          this.activeHandle = event.fingerList[0].id
        })
        .onActionUpdate((event: GestureEvent) => {
          this.activeHandle = event.fingerList[0].id
        })
    )
  }
}
