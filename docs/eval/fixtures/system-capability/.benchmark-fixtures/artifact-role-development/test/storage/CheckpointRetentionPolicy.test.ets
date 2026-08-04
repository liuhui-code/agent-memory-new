import { CheckpointRetentionPolicy } from '../../src/storage/CheckpointRetentionPolicy'

export function testCheckpointRetentionPolicyCompensation(): void {
  const policy = new CheckpointRetentionPolicy()
  policy.finalizeCheckpoint('accepted')
  policy.discardCheckpoint()
}
