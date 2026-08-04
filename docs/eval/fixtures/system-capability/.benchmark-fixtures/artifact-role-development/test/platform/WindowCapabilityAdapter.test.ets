import { WindowCapabilityAdapter } from '../../src/platform/WindowCapabilityAdapter'

export function testWindowCapabilityAdapterBoundary(): void {
  const adapter = new WindowCapabilityAdapter()
  adapter.supportsStyleMutation(26, 'convertible')
  adapter.applyStyleWhenSupported(26, 'convertible')
}
