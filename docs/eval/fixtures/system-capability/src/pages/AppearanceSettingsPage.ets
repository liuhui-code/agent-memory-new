@Component
export struct AppearanceSettingsPage {
  @State statusBarColor: string = '#ffffff'

  build() {
    TextInput({ text: this.statusBarColor })
  }
}
