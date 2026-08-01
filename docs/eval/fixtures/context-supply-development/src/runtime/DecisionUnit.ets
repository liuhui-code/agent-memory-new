export class DecisionUnit {
  evaluate(): boolean {
    return canIUse('SystemCapability.Multimedia.Audio')
  }
}
