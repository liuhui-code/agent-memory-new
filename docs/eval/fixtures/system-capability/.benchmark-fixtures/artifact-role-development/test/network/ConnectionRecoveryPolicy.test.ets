import { ConnectionRecoveryPolicy } from '../../src/network/ConnectionRecoveryPolicy'

export function testConnectionRecoveryPolicyResumeGuard(): void {
  const policy = new ConnectionRecoveryPolicy()
  policy.shouldResume('speaker', 'headphones')
  policy.recordSuccessfulResume('headphones')
}
