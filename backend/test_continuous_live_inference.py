"""
Continuous Live YOLO26 AI Inference Verification Script
Tests decoupled single-slot buffer architecture, stream FPS, AI FPS, and latency metrics on a live camera source.
"""
import json
import time
from app.services.multi_stream_yolo26 import stream_manager, StreamConfigRequest

def run_test():
    cam_id = "CAM-AMD-ITX-01"
    print(f"=== STARTING CONTINUOUS YOLO26 INFERENCE ON CAMERA: {cam_id} ===")

    # 1. Register and start decoupled continuous stream worker
    cfg = StreamConfigRequest(
        camera_id=cam_id,
        source_url="https://live.corp8.cloud/live/stream/13/index.m3u8",
        sample_fps=2.0,
        confidence_threshold=0.30
    )
    status = stream_manager.register_and_start(cfg)
    print("Initial Worker Status:", status.model_dump())

    # 2. Allow worker to run continuously for 7.5 seconds (covers warm-up + steady-state cycles)
    print("\nRunning live decoupled inference pipeline for 7.5 seconds...")
    time.sleep(7.5)

    # 3. Sample live status and latest HUD telemetry
    live_status = stream_manager.get_status(cam_id)
    latest_hud = stream_manager.get_latest_hud(cam_id)

    print("\n=== LIVE STREAM TELEMETRY REPORT ===")
    if live_status:
        print("Camera ID:", live_status.camera_id)
        print("Stream FPS (Raw Camera Ingestion):", live_status.stream_fps)
        print("AI Processed FPS:", live_status.ai_processed_fps)
        print("Inference Latency (ms):", live_status.latency_ms)
        print("Compute Device:", live_status.device)
        print("Total Frames Ingested:", live_status.total_frames_read)
        print("Total AI Inferences Executed:", live_status.total_inferences)
        print("Total Detections Logged:", live_status.total_detections)

    if latest_hud:
        print("\nLatest HUD Frame Summary:")
        print(json.dumps(latest_hud.get("summary", {}), indent=2))
        print(f"\nActive Detections in Latest HUD Frame (Count: {len(latest_hud.get('detections', []))}):")
        for d in latest_hud.get("detections", []):
            cls_name = d.get("object_class")
            conf = d.get("confidence")
            bbox = d.get("bounding_box")
            print(f" - {cls_name} (Confidence: {conf}) BBox: {bbox}")

    # 4. Cleanly stop the worker
    stopped = stream_manager.stop_stream(cam_id)
    print("\nWorker cleanly stopped:", stopped)

if __name__ == "__main__":
    run_test()
