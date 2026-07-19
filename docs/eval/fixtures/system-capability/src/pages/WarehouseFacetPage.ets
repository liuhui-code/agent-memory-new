import { FacetRecord } from '../entities/FacetRecord'

@ComponentV2
export struct WarehouseFacetPage {
  @Consumer('NavPathStack') pageStack: NavPathStack = new NavPathStack()
  @Local facets: FacetRecord[] = []

  build() {
    List() {
      ForEach(this.facets, (facet: FacetRecord) => {
        ListItem() {
          Text(facet.value).onClick(() => {
            this.pageStack.pushPathByName('WarehouseSearchPage', facet)
          })
        }
      })
    }
  }
}

