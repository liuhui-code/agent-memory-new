@Entry
@Component
struct ShipmentTimelinePage {
  @State shipments: Shipment[] = []

  build() {
    Column() {
      List() {
        ForEach(this.shipments, (shipment: Shipment) => {
          ListItem() { Text(shipment.label) }
        })
      }
      .listDirection(Axis.Vertical)
      .height('100%')
    }
  }
}
