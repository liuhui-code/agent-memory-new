export class RequestService {
  finishRequest(completed: boolean): void {
    if (!completed) {
      console.error('request timeout')
    }
  }
}
