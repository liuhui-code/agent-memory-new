export enum SourcePhase {
  Idle,
  Loading,
  Ready
}

interface SourceLoader {
  openSource(source: string): Promise<void>
}

export class SourceSwapCoordinator {
  private phase: SourcePhase = SourcePhase.Idle
  private source: string = ''

  constructor(private loader: SourceLoader) {}

  async replaceSource(nextSource: string): Promise<void> {
    this.phase = SourcePhase.Idle
    this.source = nextSource
    await this.loader.openSource(nextSource)
  }
}
