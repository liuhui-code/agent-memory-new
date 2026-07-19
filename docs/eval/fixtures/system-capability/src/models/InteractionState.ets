export class InteractionState {
  activePointer: number = 0

  selectPointer(index: number): void {
    this.activePointer = index
  }
}
