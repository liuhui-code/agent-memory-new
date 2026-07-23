import { ConfirmationDialogController } from '../dialogs/ConfirmationDialogController';

@ComponentV2
export struct ReconciliationPage {
  private dialogController: ConfirmationDialogController = new ConfirmationDialogController();

  @Builder
  completionDialog() {
    Column() {
      Text('Reconciliation completed')
      Button('Confirm')
        .onClick(() => {
          this.dialogController.finish();
        })
    }
  }
}
