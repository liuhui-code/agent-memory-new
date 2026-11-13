  import ThingViewModel from '../viewmodel/ThingViewModel';
  import { ThingViewModelArray } from '../viewmodel/TodoListViewModel'
  import { ThingComponent } from './ThingComponent';
  
  @Component
  export struct TodoListComponent {
    @ObjectLink thingViewModelArray: ThingViewModelArray;
  
    build() {
      Column() {
        List() {
          ForEach(this.thingViewModelArray, (item: ThingViewModel) => {
            // To-Do list
            ListItem() {
              ThingComponent({ thing: item })
                .margin(5)
            }
          }, (item: ThingViewModel) => {
            return item.thingName;
          })
        }
      }
    }
  }
