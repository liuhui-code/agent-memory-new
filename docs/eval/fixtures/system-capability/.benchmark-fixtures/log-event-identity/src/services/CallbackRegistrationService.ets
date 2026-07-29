import { EventLogger as callbackLogger } from '../logging/EventLogger'

const TAG = 'CallbackRegistration'

export class CallbackRegistrationService {
  register(response: string): void {
    Promise.resolve(response).then((value: string) => {
      callbackLogger.info(TAG, `REGISTER_EVENT_45C2 response accepted: ${value}`)
    })
  }
}
