export class PlaybackReadinessPolicy {
  acceptsPlaybackDuration(duration: number): boolean {
    return duration > 0
  }
}
