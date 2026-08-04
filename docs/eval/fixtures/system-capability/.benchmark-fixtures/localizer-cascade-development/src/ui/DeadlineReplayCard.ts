export class DeadlineReplayCard {
  renderEarliestDeadline(deadline: number): string {
    return `Earliest deadline: ${deadline}; insertion sequence is preserved by runtime`
  }
}
