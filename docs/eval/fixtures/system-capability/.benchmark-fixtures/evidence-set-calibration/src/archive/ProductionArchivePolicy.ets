export class ProductionArchivePolicy {
  retainProductionArchive(days: number): boolean {
    return days <= 90
  }
}
