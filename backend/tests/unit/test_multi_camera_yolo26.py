import pytest
import time
from app.services.multi_stream_yolo26 import MultiStreamYOLO26Manager, StreamConfigRequest
from app.ai.yolo26.detector import get_detector


@pytest.fixture
def multi_manager():
    mgr = MultiStreamYOLO26Manager()
    yield mgr
    mgr.stop_all()


def test_shared_detector_instance():
    det1 = get_detector()
    det2 = get_detector()
    assert det1 is det2
    assert det1.is_loaded is True


def test_independent_tracking_and_status(multi_manager):
    cfg1 = StreamConfigRequest(camera_id="CAM-TEST-01", source_url="https://live.corp8.cloud/stream/13", sample_fps=2.0)
    cfg2 = StreamConfigRequest(camera_id="CAM-TEST-02", source_url="https://live.corp8.cloud/stream/14", sample_fps=2.0)

    multi_manager.register_and_start(cfg1)
    multi_manager.register_and_start(cfg2)

    w1 = multi_manager.workers.get("CAM-TEST-01")
    w2 = multi_manager.workers.get("CAM-TEST-02")

    assert w1 is not None
    assert w2 is not None
    assert w1.tracker is not w2.tracker
    assert w1.tracker.camera_id == "CAM-TEST-01"
    assert w2.tracker.camera_id == "CAM-TEST-02"

    stat1 = multi_manager.get_camera_ai_status("CAM-TEST-01")
    stat2 = multi_manager.get_camera_ai_status("CAM-TEST-02")

    assert stat1["camera_id"] == "CAM-TEST-01"
    assert stat1["ai_enabled"] is True
    assert "inference_fps" in stat1
    assert "active_tracks" in stat1

    assert stat2["camera_id"] == "CAM-TEST-02"
    assert stat2["ai_enabled"] is True


def test_offline_camera_isolation(multi_manager):
    # Start valid camera
    multi_manager.register_and_start(
        StreamConfigRequest(camera_id="CAM-ONLINE", source_url="https://live.corp8.cloud/stream/13", sample_fps=2.0)
    )
    # Start invalid/offline camera
    multi_manager.register_and_start(
        StreamConfigRequest(camera_id="CAM-OFFLINE", source_url="https://invalid.stream/test.m3u8", sample_fps=2.0)
    )

    time.sleep(0.5)

    online_stat = multi_manager.get_camera_ai_status("CAM-ONLINE")
    offline_stat = multi_manager.get_camera_ai_status("CAM-OFFLINE")

    assert online_stat["ai_enabled"] is True
    assert offline_stat["camera_id"] == "CAM-OFFLINE"
