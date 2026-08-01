import { DialogCommitService } from './DialogCommitService'

@Component
export struct DialogCommitPanel {
  private service: DialogCommitService = new DialogCommitService()

  onConfirmDialog(draftId: string): void {
    this.service.commitDialogDraft(draftId)
  }
}
