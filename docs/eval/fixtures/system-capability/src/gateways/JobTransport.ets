export class JobTransport {
  private socket: { send: (payload: string) => Promise<void> }

  async submit(payload: string): Promise<boolean | string> {
    try {
      await this.socket.send(payload)
      return true
    } catch (error) {
      Logger.error(`job submission failed: ${error}`)
      return `${error}`
    }
  }
}
