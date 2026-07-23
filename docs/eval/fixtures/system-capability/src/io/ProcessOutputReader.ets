export class ProcessOutputReader {
  readOutput(reader: LineReader): string {
    const lines: string[] = []
    let line = reader.readLine()
    while (line !== null) {
      lines.push(line)
      line = reader.readLine()
    }
    return lines.join('\n')
  }
}
