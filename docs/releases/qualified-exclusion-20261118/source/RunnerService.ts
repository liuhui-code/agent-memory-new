import { AlphaService } from './AlphaService'
export class RunnerService {
  run(): string {
    const worker = new AlphaService()
    return worker.start()
  }
}
