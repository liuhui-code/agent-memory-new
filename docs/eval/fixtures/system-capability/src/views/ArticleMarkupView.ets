import { ArticleRecord } from '../entities/ArticleRecord'

@ComponentV2
export struct ArticleMarkupView {
  @Param article: ArticleRecord = new ArticleRecord()

  build() {
    Column() {
      Text(this.article.title)
      Text(this.cleanedBody())
    }
  }

  cleanedBody(): string {
    return this.article.markupBody
      .replace('<br />', '\n')
      .replace(new RegExp('<[^>]+>'), '')
  }
}

