export class SharedRecordCollector {
  collect(records: ShareRecord[]): string {
    let output = ''
    for (const record of records) {
      if (record.kind === 'markup') {
        output = this.convertMarkup(record.content)
      } else {
        output = record.content
      }
    }
    return output
  }
}
