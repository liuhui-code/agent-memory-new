import { LogSink } from './LogSink'

export class DomainLogger {
  private sink: LogSink = new LogSink()

  report(message: string): void {
    this.sink.emit(message)
  }
}
