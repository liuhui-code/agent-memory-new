import { AccountUpdateService } from '../services/AccountUpdateService'

@Entry
@Component
export struct AccountSettingsPage {
  @State displayName: string = ''
  private updateService: AccountUpdateService = new AccountUpdateService()

  saveAccount(): void {
    if (this.displayName.trim().length === 0) {
      promptAction.showToast({ message: 'Required display name' })
      return
    }
    this.updateService.dispatchUpdate(this.displayName)
  }

  build() {}
}
