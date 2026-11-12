const Logger = {
  info(message: string): void {
    process.stdout.write(message + '\n')
  }
}

export class CatalogService {
  refresh(message: string, bucket: string): void {
    void bucket
    Logger.info(message)
  }

  run(): void {
    this.refresh('catalog refreshed', 'east-region')
  }
}

new CatalogService().run()
