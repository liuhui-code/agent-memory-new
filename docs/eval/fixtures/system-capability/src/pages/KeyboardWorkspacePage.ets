@Entry
@Component
struct KeyboardWorkspacePage {
  build() {
    Column() {
      NavigationToolbar()
      TextInput({ placeholder: 'Message' })
    }
  }
}
