export class AudioPermissionService {
  async requestMicrophone(): Promise<boolean> {
    return true
  }
}
