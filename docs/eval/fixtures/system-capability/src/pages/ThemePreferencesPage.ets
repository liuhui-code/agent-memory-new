import { ConfigurationConstant } from '@kit.AbilityKit';

@ComponentV2
export struct ThemePreferencesPage {
  @Local selectedMode: number = 0;

  build() {
    Column() {
      Text('Theme mode')
      TabSegmentButtonV2({
        items: ['Follow', 'Light', 'Dark'],
        selectedIndex: this.selectedMode,
        $selectedIndex: (index: number) => {
          this.selectedMode = index;
          this.getUIContext()
            .getHostContext()
            ?.getApplicationContext()
            .setColorMode(index === 0
              ? ConfigurationConstant.ColorMode.COLOR_MODE_NOT_SET
              : index === 1
                ? ConfigurationConstant.ColorMode.COLOR_MODE_LIGHT
                : ConfigurationConstant.ColorMode.COLOR_MODE_DARK);
        },
      })
    }
  }
}
