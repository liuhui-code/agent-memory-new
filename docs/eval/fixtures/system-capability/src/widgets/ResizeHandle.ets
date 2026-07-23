@Component
export struct ResizeHandle {
  build() {
    Circle()
      .gesture(
        PanGesture().onActionUpdate((event: GestureEvent) => {
          const horizontalDelta = event.offsetX
        })
      )
  }
}
