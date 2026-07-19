import { pasteboard } from '@kit.BasicServicesKit'

export class ClipboardContentReader {
  async readPlainText(): Promise<string> {
    const board = pasteboard.getSystemPasteboard()
    const data = await board.getData()
    if (data.getRecordCount() === 0) {
      return ''
    }
    return data.getRecordAt(0).plainText ?? ''
  }
}
