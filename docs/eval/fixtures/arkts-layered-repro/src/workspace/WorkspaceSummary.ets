@Component
export struct WorkspaceSummary {
  build() {
    Text('workspace selected')
      .onClick(() => Logger.info('workspace summary opened'))
  }
}
