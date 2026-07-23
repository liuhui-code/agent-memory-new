export class SeatStore {
  private selectedSeats: boolean[] = []

  replaceSeat(index: number, selected: boolean): void {
    this.selectedSeats[index] = selected
  }
}
