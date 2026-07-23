import { ProfileService } from '../services/ProfileService'

@Entry
@Component
struct ProfilePage {
  private profileService: ProfileService = new ProfileService()

  aboutToAppear(): void {
    this.profileService.loadProfile()
  }

  build() {}
}
