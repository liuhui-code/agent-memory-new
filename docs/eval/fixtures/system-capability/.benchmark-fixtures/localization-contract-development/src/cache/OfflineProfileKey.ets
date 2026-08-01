export class OfflineProfileKey {
  public static slotOf(alias: string): string {
    let safe = ''
    for (let index = 0; index < alias.length; index++) {
      const character = alias.charAt(index)
      safe += /[a-zA-Z0-9_-]/.test(character) ? character : '_'
    }
    return `${safe.substring(0, 48)}_${alias.length}`
  }
}
