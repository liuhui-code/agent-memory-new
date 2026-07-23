@Entry
@Component
struct ShortcutSearchPage {
  build() {
    Column() {
      TextInput({ placeholder: 'Search' })
        .onKeyEvent((event: KeyEvent) => {
          if (event.keyCode === KeyCode.KEYCODE_BACK) {
            return true
          }
          return false
        })
    }
  }
}
