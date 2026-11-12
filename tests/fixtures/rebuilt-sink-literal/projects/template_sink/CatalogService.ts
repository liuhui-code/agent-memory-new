const Logger = {
  info(message: string): void {
    process.stdout.write(message + '\n')
  }
}

export class CatalogService {
  refresh(bucket: string): void {
    Logger.info(`catalog refreshed: ${bucket}`)
  }

  run(): void {
    this.refresh('east-region')
  }
}

new CatalogService().run()
