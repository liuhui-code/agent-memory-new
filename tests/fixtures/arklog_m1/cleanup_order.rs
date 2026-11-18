#[test]
fn retirement_receipt_precedes_replacement_commit() {
    use crate::{ConnectionState, StreamState};
    use std::time::{Duration, Instant};
    let mut controller = ArkLogController::new(fixture("switching-devices-hdc.sh"), vec![online("USB-A")])
        .expect("controller");
    controller.start_stream().expect("start A");
    let old = controller.active_stream_id().unwrap().to_string();
    controller.request_device_refresh().expect("discover A offline and B online");
    let deadline = Instant::now() + Duration::from_secs(3);
    while controller.connection_state() == &ConnectionState::Refreshing {
        assert!(Instant::now() < deadline, "fixture discovery did not finish");
        controller.pump_background_tasks().expect("actual background owner");
        std::thread::sleep(Duration::from_millis(2));
    }
    assert_eq!(controller.selected_device().unwrap().id, "USB-B");
    let pending_receipt = controller.stream_stop.is_running();
    let premature_binding = controller.active_stream_id().map(str::to_string);
    while controller.stream_stop.is_running() || controller.active_stream_id().is_none() {
        assert!(Instant::now() < deadline, "cleanup/replacement fixture did not finish");
        controller.pump_log_batches().unwrap();
        controller.pump_background_tasks().expect("apply old receipt then reconcile");
        std::thread::sleep(Duration::from_millis(2));
    }
    let current = controller.active_stream_id().unwrap().to_string();
    let final_state = controller.stream_state().clone();
    println!("M1_TRACE old={old} receipt_pending={pending_receipt} premature={premature_binding:?} current={current} state={final_state:?}");
    assert!(pending_receipt, "test must reach the actual unconsumed Stop receipt boundary");
    assert!(premature_binding.is_none(), "replacement must wait for retirement receipt");
    assert_ne!(old, current);
    assert_eq!(final_state, StreamState::Streaming, "retired completion must not clobber replacement state");
    controller.stop_stream().expect("stop B fixture");
}
