export enum CommandPhase {
  Idle,
  Prepared,
  Playing,
  Released
}

export class CommandEligibility {
  canSeek(phase: CommandPhase): boolean {
    return phase === CommandPhase.Prepared || phase === CommandPhase.Playing
  }

  canAdjustVolume(phase: CommandPhase): boolean {
    return phase === CommandPhase.Prepared || phase === CommandPhase.Playing
  }
}
