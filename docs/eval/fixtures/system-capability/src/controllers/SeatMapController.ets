export interface SeatState {
  selected: boolean
}

export class SeatMapController {
  private seats: SeatState[] = []

  onSeatTapped(index: number): void {
    this.seats[index].selected = !this.seats[index].selected
    this.seats[index - 1].selected = this.seats[index].selected
    this.seats[index + 1].selected = this.seats[index].selected
  }
}
