export class DisplayPreferenceBootstrap {
  static async applyStoredDensity(): Promise<void> {
    const savedDensity = await PreferencesStore.readString('display_density')
    if (savedDensity.length === 0) {
      return
    }
    DisplaySettings.setDensity(savedDensity)
  }

  static configureDefaults(): void {
    DisplaySettings.setPalette('system')
  }
}
