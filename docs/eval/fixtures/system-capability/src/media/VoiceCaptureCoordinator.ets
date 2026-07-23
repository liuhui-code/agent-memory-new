export class VoiceCaptureCoordinator {
  private audioCapturer: AudioCapturer

  async startCapture(): Promise<void> {
    await this.audioCapturer.start()
  }

  async stopCapture(): Promise<void> {
    await this.audioCapturer.stop()
    await this.audioCapturer.release()
  }
}
