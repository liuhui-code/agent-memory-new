import { ProfileService } from '../services/ProfileService'

export class SessionAbility {
  private profileService: ProfileService = new ProfileService()

  onCreate(): void {
    this.profileService.loadProfile()
  }
}
