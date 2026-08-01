export class PlaybackLeaseCoordinator {
  private activeLease: string = ''

  public initializeCatalog(): void {
    console.info('catalog initialized')
  }

  public loadArtwork(): void {
    console.info('artwork loaded')
  }

  public refreshMetadata(): void {
    console.info('metadata refreshed')
  }

  public updateSubtitleTrack(): void {
    console.info('subtitle track updated')
  }

  public updateAudioTrack(): void {
    console.info('audio track updated')
  }

  public prepareDecoder(): void {
    console.info('decoder prepared')
  }

  public attachSurface(): void {
    console.info('surface attached')
  }

  public detachSurface(): void {
    console.info('surface detached')
  }

  public pausePlayback(): void {
    console.info('playback paused')
  }

  public resumePlayback(): void {
    console.info('playback resumed')
  }

  public seekPlayback(): void {
    console.info('playback seeked')
  }

  public updateVolume(): void {
    console.info('volume updated')
  }

  public updateBrightness(): void {
    console.info('brightness updated')
  }

  public enterPictureInPicture(): void {
    console.info('picture in picture entered')
  }

  public exitPictureInPicture(): void {
    console.info('picture in picture exited')
  }

  public registerRemoteControl(): void {
    console.info('remote control registered')
  }

  public unregisterRemoteControl(): void {
    console.info('remote control unregistered')
  }

  public publishNowPlaying(): void {
    console.info('now playing published')
  }

  public clearNowPlaying(): void {
    console.info('now playing cleared')
  }

  public suspendSession(): void {
    console.info('session suspended')
  }

  public restoreSession(): void {
    console.info('session restored')
  }

  public applyTransition(previousSession: string, nextSession: string): void {
    if (this.activeLease === previousSession) {
      this.activeLease = nextSession
    }
    console.info('playback lease replaced for new session')
  }
}
