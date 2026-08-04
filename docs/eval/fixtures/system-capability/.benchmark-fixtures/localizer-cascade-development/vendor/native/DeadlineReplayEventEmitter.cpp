void DeadlineReplayEventEmitter::emitReadyWorkOrder(
    double earliestDeadline,
    int insertionSequence) {
  emit("resumed work queue earliest deadline insertion sequence unstable order");
}
