export class ConfirmationDialogController {
  constructor(private readonly controller: DialogController) {
  }

  finish(): void {
    this.controller.close();
  }
}
