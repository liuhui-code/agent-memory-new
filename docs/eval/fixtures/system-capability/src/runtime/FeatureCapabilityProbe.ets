import { bundleManager } from '@kit.AbilityKit'

export class FeatureCapabilityProbe {
  async supportsShareExtension(): Promise<boolean> {
    const info = await bundleManager.getBundleInfoForSelf(
      bundleManager.BundleFlag.GET_BUNDLE_INFO_WITH_EXTENSION_ABILITY,
    )
    return info.extensionAbilityInfo.length > 0
  }
}
