@Component
export struct DeferredNotificationBanner {
  @State pendingSignal: string = ''

  build() {
    Text(`deferred notification ${this.pendingSignal} before surface ready`)
  }
}
