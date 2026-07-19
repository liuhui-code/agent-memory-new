@Entry
@Component
struct VoiceMessagePage {
  @State recording: boolean = false

  async toggleRecording(): Promise<void> {
    this.recording = !this.recording
  }

  build() {
    Button(this.recording ? 'Stop' : 'Record')
  }
}
