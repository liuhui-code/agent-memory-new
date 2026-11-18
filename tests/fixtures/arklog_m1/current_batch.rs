// Test-only queue ingress adapter. It calls the actual Controller pump; no gate is reimplemented.
use super::ArkLogController;
use arklog_core::{DeviceLogDevice, DeviceLogOutputBatch};
use std::path::PathBuf;

fn online(id: &str) -> DeviceLogDevice {
    DeviceLogDevice {
        id: id.to_string(), label: id.to_string(), status: "online".to_string(),
        detail: format!("{id} Connected"),
    }
}

fn fixture(name: &str) -> String {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests/fixtures").join(name).to_string_lossy().into_owned()
}

fn enqueue(controller: &ArkLogController, stream: &str, device: &str, line: &str) {
    controller.batch_sender.send(DeviceLogOutputBatch {
        stream_id: stream.to_string(), device_id: device.to_string(), lines: vec![line.to_string()],
    }).expect("test-only controlled queue ingress");
}

#[test]
fn current_batch_is_accepted() {
    let mut controller = ArkLogController::new(fixture("fake-hdc.sh"), vec![online("USB-01")])
        .expect("controller");
    controller.start_stream().expect("start actual Runtime with fixture executable");
    let stream = controller.active_stream_id().unwrap().to_string();
    enqueue(&controller, &stream, "USB-01", "M1_CURRENT");
    controller.pump_log_batches().expect("actual public pump");
    let rows = controller.state_mut().visible_window(100).unwrap();
    assert!(rows.iter().any(|line| line == "M1_CURRENT"), "valid current batch must be retained");
    controller.stop_stream().expect("stop fixture");
}
