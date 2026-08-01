export interface ResultListener {
  onReady(surfaceId: string): void
  onFailure(code: number, message: string): void
}

export class NativeResultBoundary {
  attach(runtime: NativeRuntime, listener: ResultListener): void {
    runtime.setObserver({
      onReady: (surfaceId: string) => {
        listener.onReady(surfaceId)
      },
      onFailure: (code: number, message: string) => {
        listener.onFailure(code, message)
      }
    })
  }
}
