import { StateModel } from '../model/StateModel'

@Component
struct ControlPanel {
  private state: StateModel = new StateModel()
  build() { Text('Controls') }
  clear() { this.state.reset() }
}
