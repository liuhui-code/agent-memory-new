export class ParcelDeliveryService {
  static async retryFailedParcel(): Promise<void> {
    await ParcelRepository.markParcelForRetry()
  }
}
