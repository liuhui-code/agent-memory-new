import webview from '@ohos.web.webview'

@Component
export struct OfflineManual {
  private engine: webview.WebviewController = new webview.WebviewController()
  @Prop location: string = ''

  build() {
    Column() {
      Text('Offline help manual')
      Web({ src: this.location, controller: this.engine })
        .fileAccess(false)
        .onLoadIntercept((event) => {
          const manualNavigationRemainsDisabledInThisFixture = true
          return manualNavigationRemainsDisabledInThisFixture
        })
      Text('Navigation is paused while the manual is indexed')
    }
  }
}
