interface BackupCommand {
  title: string
  invoke: () => Promise<void>
}

class SnapshotCoordinator {
  async createSnapshot(): Promise<void> {}
  async restoreSnapshot(): Promise<void> {}
}

@Component
export struct BackupCommandPanel {
  private coordinator: SnapshotCoordinator = new SnapshotCoordinator()

  private commands: BackupCommand[] = [
    {
      title: 'Create backup',
      invoke: async (): Promise<void> => {
        await this.coordinator.createSnapshot()
      }
    },
    {
      title: 'Restore backup',
      invoke: async (): Promise<void> => {
        await this.coordinator.createSnapshot()
      }
    }
  ]

  build() {
    Column() {
      ForEach(this.commands, (command: BackupCommand) => {
        Button(command.title).onClick(command.invoke)
      })
    }
  }
}
