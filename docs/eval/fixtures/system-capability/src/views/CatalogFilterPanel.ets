import { FilterToggle } from './FilterToggle'

@Component
export struct CatalogFilterPanel {
  @Prop denseMode: boolean = false

  build() {
    Row() {
      Text('Filters')
      FilterToggle({
        denseMode: this.denseMode
      })
    }
  }
}
