import { CatalogFilterPanel } from '../views/CatalogFilterPanel'

@Entry
@Component
struct CatalogPage {
  @State compactFilters: boolean = false

  private resolveDenseMode(): boolean {
    return this.compactFilters
  }

  build() {
    Column() {
      Text('Catalog')
      CatalogFilterPanel({
        denseMode: this.resolveDenseMode()
      })
    }
  }
}
