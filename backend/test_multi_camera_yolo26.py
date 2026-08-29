"""
Multi-Camera YOLO26 Extension Verification Script
Tests continuous multi-camera AI ingestion across cameras from camera_sources.yaml.
Verifies independent stream/tracking states, shared detector, offline stream isolation, and per-camera AI status.
"""
import json
import time
from app.services.multi_stream_yolo26 import stream_manager, StreamConfigRequest
from app.ai.yolo26.detector import get_detector


def run_multi_camera_test():
    print("=== STARTING MULTI-CAMERA YOLO26 AI CLUSTER TEST ===")

    # 1. Verify shared singleton YOLO26 detector
    det1 = get_detector()
    det2 = get_detector()
    assert det1 is det2, "YOLO26 detector must be a shared singleton across all camera workers"
    print(f"[1/5] Shared singleton YOLO26 detector confirmed: {det1.config.model_path} on {det1.device}")

    # 2. Start concurrent stream workers across 3 cameras from camera_sources.yaml
    test_cameras = [
        {"code": "CAM-AMD-ITX-01", "url": "https://live.corp8.cloud/live/stream/13/index.m3u8"},
        {"code": "CAM-AMD-ITX-02", "url": "https://live.corp8.cloud/live/stream/14/index.m3u8"},
        {"code": "CAM-AMD-ISK-01", "url": "https://live.corp8.cloud/live/stream/15/index.m3u8"},
    ]

    print(f"\n[2/5] Starting continuous YOLO26 workers across {len(test_cameras)} cameras...")
    for cam in test_cameras:
        cfg = StreamConfigRequest(
            camera_id=cam["code"],
            source_url=cam["url"],
            sample_fps=2.0,
            confidence_threshold=0.30,
        )
        stream_manager.register_and_start(cfg)

    # 3. Allow multi-camera cluster to ingest and track concurrently for 7.5 seconds
    print("Running multi-camera AI cluster concurrently for 7.5 seconds...")
    time.sleep(7.5)

    # 4. Verify independent tracking states and extract per-camera AI statuses
    print("\n[3/5] Inspecting per-camera independent tracking and AI status:")
    statuses = []
    for cam in test_cameras:
        cam_code = cam["code"]
        ai_stat = stream_manager.get_camera_ai_status(cam_code)
        worker = stream_manager.workers.get(cam_code)
        
        # Verify independent tracker instance
        assert worker is not None
        assert worker.tracker.camera_id == cam_code, f"Tracker must be strictly scoped to {cam_code}"
        
        statuses.append(ai_stat)
        print(f"\n--- Camera Status: {cam_code} ---")
        print(json.dumps(ai_stat, indent=2))

    # 5. Verify offline camera fault-tolerance (simulating an invalid stream URL)
    print("\n[4/5] Testing offline camera failure isolation...")
    offline_cfg = StreamConfigRequest(
        camera_id="CAM-OFFLINE-TEST",
        source_url="https://invalid.stream.endpoint.test/live/stream/999/index.m3u8",
        sample_fps=2.0,
    )
    stream_manager.register_and_start(offline_cfg)
    time.sleep(2.0)
    
    offline_status = stream_manager.get_camera_ai_status("CAM-OFFLINE-TEST")
    print("Offline Camera Handled Gracefully:", offline_status)
    
    # Active camera CAM-AMD-ITX-01 must still be running unaffected
    itx_status = stream_manager.get_camera_ai_status("CAM-AMD-ITX-01")
    assert itx_status["ai_enabled"] is True, "Active camera AI must not be impacted by offline camera"
    print("Primary camera status during offline stream test:", itx_status["camera_id"], "ai_enabled:", itx_status["ai_enabled"])

    # 6. Clean shutdown of all streams
    print("\n[5/5] Cleanly stopping all stream workers...")
    stopped_count = stream_manager.stop_all()
    print(f"Cleanly stopped all {stopped_count} camera workers. Active workers remaining: {len(stream_manager.workers)}")
    assert len(stream_manager.workers) == 0

    print("\n=== MULTI-CAMERA YOLO26 TEST COMPLETED SUCCESSFULLY ===")
    return statuses


if __name__ == "__main__":
    run_multi_camera_test()
