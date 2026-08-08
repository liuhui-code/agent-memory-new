import { SessionState } from './SessionState'

export class RetryCoordinator {
  retry(state: SessionState): void {
    state.pending = true
  }
}
