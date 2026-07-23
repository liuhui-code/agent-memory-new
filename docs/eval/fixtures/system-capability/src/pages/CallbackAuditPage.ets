@Component
struct CallbackAuditPage {
  @State private refreshed: boolean = false

  private refreshNow(): void {
    this.refreshed = true
  }

  build(): void {
    Button('Refresh').onClick(this.refreshNow)
  }
}
