export const MotionGeometryPolicy = {
  viewportVisibility: (width: number, page: number): number => {
    return width > 840 ? page : 0
  },

  frozenTargetX: (width: number, page: number): number => {
    return MotionGeometryPolicy.viewportVisibility(width, page) * width
  },
}
