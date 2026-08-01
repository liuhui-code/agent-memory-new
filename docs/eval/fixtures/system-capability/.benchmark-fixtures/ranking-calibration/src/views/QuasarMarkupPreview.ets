@Component
export struct QuasarMarkupPreview {
  @Prop body: string = ''

  private cleanQuasarBody(): string {
    return this.body.replace(/<[^>]+>/g, '')
  }

  build(): void {
    Text(this.cleanQuasarBody())
  }
}
