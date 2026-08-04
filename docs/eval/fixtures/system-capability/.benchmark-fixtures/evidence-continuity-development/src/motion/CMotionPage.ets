export class MotionPage {
  viewportVisibility(width: number, page: number): number {
    return MotionGeometryPolicy.viewportVisibility(width, page)
  }

  frozenTargetX(width: number, page: number): number {
    return MotionGeometryPolicy.frozenTargetX(width, page)
  }
}
