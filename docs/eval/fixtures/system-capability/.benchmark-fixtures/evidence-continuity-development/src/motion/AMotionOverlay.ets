export class MotionOverlay {
  applyViewportVisibility(width: number, page: number): number {
    return MotionGeometryPolicy.viewportVisibility(width, page)
  }

  freezeTargetX(width: number, page: number): number {
    return MotionGeometryPolicy.frozenTargetX(width, page)
  }
}
