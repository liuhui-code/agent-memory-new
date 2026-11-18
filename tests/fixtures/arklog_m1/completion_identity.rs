#[test]
fn completion_keeps_origin_while_another_stream_is_active() {
    use arklog_core::{DeviceLogRuntime, LogBatchSink};
    use std::sync::Arc;
    use std::time::{Duration, Instant};
    struct Sink;
    impl LogBatchSink for Sink { fn deliver(&self, _batch: DeviceLogOutputBatch) {} }
    let executable = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../arklog-core/tests/fixtures/fake-hdc.sh");
    let runtime = DeviceLogRuntime::new(executable.to_string_lossy());
    let retiring = runtime.start_stream("EXIT-01", Arc::new(Sink)).unwrap();
    let current = runtime.start_stream("USB-01", Arc::new(Sink)).unwrap();
    let deadline = Instant::now() + Duration::from_secs(3);
    let observed = loop {
        if let Some(exit) = runtime.finished_stream_status(&retiring.stream_id).unwrap() { break exit; }
        assert!(Instant::now() < deadline, "controlled exiting fixture did not finish");
        std::thread::sleep(Duration::from_millis(2));
    };
    println!("M1_TRACE requested={} active={} observed={}", retiring.stream_id, current.stream_id, observed.stream_id);
    assert_eq!(observed.stream_id, retiring.stream_id, "completion must keep its origin, not current binding");
    let reaped = runtime.reap_finished_stream(&retiring.stream_id).unwrap().unwrap();
    assert_eq!(reaped.stream_id, retiring.stream_id);
    assert!(runtime.has_stream(&current.stream_id), "retiring completion must preserve current stream");
    runtime.stop_stream(&current.stream_id).unwrap();
}
