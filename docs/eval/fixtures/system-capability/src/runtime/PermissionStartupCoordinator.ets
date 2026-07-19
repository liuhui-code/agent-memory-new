export class PermissionStartupCoordinator {
  constructor(
    private accessManager: AccessManager,
    private context: Context,
    private sessionService: SessionService,
  ) {}

  async startSession(): Promise<void> {
    const result = await this.accessManager.requestPermissionsFromUser(
      this.context,
      ['ohos.permission.MICROPHONE'],
    )
    if (result.authResults.some(value => value !== 0)) {
      return
    }
    await this.sessionService.start()
  }
}
