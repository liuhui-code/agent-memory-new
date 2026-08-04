export class MotionController {
  prepareViewportVisibility(width: number, page: number): number {
    return MotionGeometryPolicy.viewportVisibility(width, page)
  }

  prepareFrozenTargetX(width: number, page: number): number {
    return MotionGeometryPolicy.frozenTargetX(width, page)
  }
}
