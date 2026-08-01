export class DialogCommitService {
  commitDialogDraft(draftId: string): void {
    DialogStore.persist(draftId)
  }
}
