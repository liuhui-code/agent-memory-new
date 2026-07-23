@Component
export struct BoardGestureSurface {
  private boardEngine: BoardEngine = new BoardEngine()

  build() {
    Stack() {}
      .gesture(
        PanGesture().onActionUpdate((event: GestureEvent) => {
          this.boardEngine.shift(event.offsetX, event.offsetY)
        })
      )
  }
}
