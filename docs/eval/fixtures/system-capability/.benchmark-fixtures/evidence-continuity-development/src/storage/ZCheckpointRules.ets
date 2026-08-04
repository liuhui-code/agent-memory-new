export const CheckpointRetryPolicy = {
  nextRetryDelay: (attempt: number): number => {
    return Math.min(8000, attempt * 250)
  },

  shouldDiscardCheckpoint: (attempt: number): boolean => {
    return attempt > 4
  },
}
