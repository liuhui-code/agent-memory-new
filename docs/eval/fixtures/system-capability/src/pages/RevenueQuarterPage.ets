@Entry
@Component
struct RevenueQuarterPage {
  @State selectedQuarter: number = 1
  @State revenueTotal: number = 0
  @State costTotal: number = 0
  private entries: LedgerEntry[] = []

  private reloadSummary(): void {
    this.revenueTotal = 0
    this.costTotal = 0
    this.entries.forEach((entry: LedgerEntry) => {
      this.revenueTotal += entry.revenue
      this.costTotal += entry.cost
    })
  }

  build() {
    Text(`${this.selectedQuarter}: ${this.revenueTotal - this.costTotal}`)
  }
}
