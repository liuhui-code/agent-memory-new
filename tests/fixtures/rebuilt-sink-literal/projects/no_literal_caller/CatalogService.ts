const Logger = {
  info(message: string): void {
    process.stdout.write(message + '\n')
  }
}

export class CatalogService {
  refresh(bucket: string): void {
    void bucket
    Logger.info('catalog refreshed')
  }

  run(): void {
    const bucket: string = 'east-region'
    this.refresh(bucket)
  }
}

new CatalogService().run()
