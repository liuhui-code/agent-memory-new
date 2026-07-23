import { ProductRecord } from '../entities/ProductRecord'

export class ProductSearchService {
  async search(query: string): Promise<ProductRecord[]> {
    const sql = 'SELECT id, name FROM products WHERE name LIKE ?'
    return this.queryProducts(sql, [query])
  }

  private async queryProducts(sql: string, args: string[]): Promise<ProductRecord[]> {
    return []
  }
}

