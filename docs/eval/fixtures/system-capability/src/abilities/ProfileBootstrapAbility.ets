import { preferences } from '@kit.ArkData';
import { AppStorageV2 } from '@kit.ArkUI';
import { UIAbility } from '@kit.AbilityKit';
import { ProfileList } from '../models/ProfileList';

function saveProfileData(context: Context): void {
  const profilePreferences = preferences.getPreferencesSync(context, { name: 'Profile' });
  const profiles = AppStorageV2.connect<ProfileList>(ProfileList, () => new ProfileList())!;
  profilePreferences.putSync('profiles', JSON.stringify(profiles));
  profilePreferences.flushSync();
}

export default class ProfileBootstrapAbility extends UIAbility {
  onCreate(): void {
    const profilePreferences = preferences.getPreferencesSync(this.context, { name: 'Profile' });
    const profiles = new ProfileList(
      ...JSON.parse(profilePreferences.getSync('sessions', '[]') as string),
    );
    AppStorageV2.connect<ProfileList>(ProfileList, () => profiles);
  }

  onBackground(): void {
    saveProfileData(this.context);
  }
}
