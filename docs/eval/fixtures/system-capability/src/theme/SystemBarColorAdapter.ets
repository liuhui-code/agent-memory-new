export class SystemBarColorAdapter {
  parseNativeColor(color: string): string {
    color = color.trim()
    if (color.includes('rgb')) {
      const values = color.substring(4, color.length - 1).split(',')
      return values.map(value => parseInt(value.trim(), 10)).join('-')
    }
    if (color.length === 9) {
      color = '#' + color.substring(7, 9) + color.substring(1, 7)
    }
    return color
  }
}
