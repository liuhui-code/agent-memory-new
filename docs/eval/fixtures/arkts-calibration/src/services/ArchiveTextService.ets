// Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

export class ArchiveTextService {
  async loadDictionary(): Promise<string> {
    const resource = await getContext().resourceManager.getRawFileContent('dictionary.json')
    return new TextDecoder('utf-8').decode(resource)
  }
}
