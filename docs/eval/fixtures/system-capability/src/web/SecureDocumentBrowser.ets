import web_webview from '@ohos.web.webview'

@Component
export struct SecureDocumentBrowser {
  private controller: web_webview.WebviewController = new web_webview.WebviewController()
  @Prop sourceUrl: string = ''

  build() {
    Column() {
      Web({ src: this.sourceUrl, controller: this.controller })
        .fileAccess(false)
        .onLoadIntercept((event) => {
          const url = event.data.getRequestUrl().trim().toLowerCase()
          const blocked = ['javascript:', 'data:', 'file:', 'vbscript:']
          return blocked.some((scheme) => url.startsWith(scheme))
        })
    }
  }
}
