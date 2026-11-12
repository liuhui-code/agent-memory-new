const Logger = {
  info(message: string): void {
    process.stdout.write(message + '\n')
  }
}

export class CatalogService {
  refresh(bucket: string, message: string): void {
    void bucket
    Logger.info(message)
  }

  run(): void {
    this.refresh('east-region', 'catalog refreshed')
  }
}

new CatalogService().run()
