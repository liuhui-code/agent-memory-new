  import ThingModel from '../model/ThingModel';
  
  @Observed
  export default class ThingViewModel {
    @Track public thingName: string = 'Todo';
    @Track public isFinish: boolean = false;
    public context: Context = AppStorage.get('context')!;
  
    updateTask(thing: ThingModel) {
      this.thingName = thing.thingName;
      this.isFinish = thing.isFinish;
    }
  
    updateIsFinish(): void {
      this.isFinish = !this.isFinish;
    }
  
    addSuffixes(): void {
      // In the resources\base\element\string.json file, set name to 'la_la' and value to a non-null string.
      this.thingName += this.context.resourceManager.getStringSync($r('app.string.la_la').id);
    }
  }
