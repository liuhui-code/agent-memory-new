  import ThingViewModel from '../viewmodel/ThingViewModel';
  
  @Component
  export struct ThingComponent {
    @ObjectLink thing: ThingViewModel;
  
    @Builder
    displayIcon(icon: Resource) {
      Image(icon)
        .width(28)
        .height(28)
        .onClick(() => {
          this.thing.updateIsFinish(); // When a click event occurs at the View layer, call the ViewModel-layer method updateIsFinish to process the logic.
        })
        .id(this.thing.thingName)
    }
  
    build() {
      // To-Do list
      Row({ space: 15 }) {
        if (this.thing.isFinish) {
          // Replace $r('app.media.finished') with the actual resource file.
          this.displayIcon($r('app.media.finished'));
        } else {
          // Replace $r('app.media.unfinished') with the actual resource file.
          this.displayIcon($r('app.media.unfinished'));
        }
  
        Text(`${this.thing.thingName}`)
          .fontSize(24)
          .decoration({ type: this.thing.isFinish ? TextDecorationType.LineThrough : TextDecorationType.None })
          .onClick(() => {
            this.thing.addSuffixes(); // When a click event occurs at the View layer, call the ViewModel-layer method addSuffixes to process the logic.
          })
      }
      .height('8%')
      .width('90%')
      .padding({ left: 15 })
      .opacity(this.thing.isFinish ? 0.3 : 1)
      .border({ width: 1 })
      .borderColor(Color.White)
      .borderRadius(25)
      .backgroundColor(Color.White)
    }
  }
