export class ProductionQuotaPolicy {
  enforceProductionQuota(bytes: number): boolean {
    return bytes <= 4096
  }
}
