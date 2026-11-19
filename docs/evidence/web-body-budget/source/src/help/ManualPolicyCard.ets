@Component
export struct ManualPolicyCard {
  build() {
    Column() {
      Text('WebView file access and URL navigation policy')
      Text('The offline manual does not open local content')
    }
  }
}
