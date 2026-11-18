#[test]
fn same_device_reconnect_rejects_prior_stream_batches() {
    let mut controller = ArkLogController::new(fixture("fake-hdc.sh"), vec![online("USB-01")])
        .expect("controller");
    controller.start_stream().expect("first actual stream");
    let old = controller.active_stream_id().unwrap().to_string();
    controller.stop_stream().expect("reap first stream");
    controller.start_stream().expect("reconnect same device");
    let current = controller.active_stream_id().unwrap().to_string();
    assert_ne!(old, current, "same device reconnect needs a new stream identity");
    // Explicit fault injection at the transport queue: no claim that the joined
    // production worker can naturally emit after reap. This tests the real fence.
    enqueue(&controller, &old, "USB-01", "M1_STALE");
    enqueue(&controller, &current, "USB-01", "M1_CURRENT");
    controller.pump_log_batches().expect("actual public pump");
    let rows = controller.state_mut().visible_window(100).unwrap();
    println!("M1_TRACE old={old} current={current} device=USB-01 rows={rows:?}");
    assert!(rows.iter().any(|line| line == "M1_CURRENT"), "current generation must remain usable");
    assert!(!rows.iter().any(|line| line == "M1_STALE"), "prior generation must not commit on same device");
    controller.stop_stream().expect("stop fixture");
}
