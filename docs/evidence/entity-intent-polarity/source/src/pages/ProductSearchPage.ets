import { ProductRecord } from '../entities/ProductRecord'
import { ProductSearchService } from '../services/ProductSearchService'

@ComponentV2
export struct ProductSearchPage {
  @Local query: string = ''
  @Local products: ProductRecord[] = []
  private service: ProductSearchService = new ProductSearchService()

  async submitSearch(): Promise<void> {
    this.products = await this.service.search(this.query)
  }

  build() {
    Column() {
      Search({ value: $$this.query }).onSubmit(() => this.submitSearch())
      List() {
        ForEach(this.products, (product: ProductRecord) => {
          ListItem() { Text(product.name) }
        })
      }
    }
  }
}

