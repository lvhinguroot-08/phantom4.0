"""
YOLO26 Live CCTV Pipeline Benchmark Script
Measures real performance metrics:
- Input FPS
- AI Inference FPS
- Approximate Inference Time (ms)
- End-to-End Latency (ms)
- Device
- Memory Usage (MB)
"""
import os
import sys
import time
import psutil
import numpy as np
import cv2
from app.ai.yolo26.detector import get_detector
from app.ai.yolo26.tracker import YOLO26Tracker
from app.services.multi_stream_yolo26 import CameraStreamWorker, StreamConfigRequest


def get_process_memory_mb():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)


def benchmark_raw_inference(num_frames=20, imgsz=(640, 640)):
    print(f"\n--- 1. Raw YOLO26 Detector Benchmark ({num_frames} frames, resolution {imgsz}) ---")
    detector = get_detector()
    device = detector.device
    print(f"Device: {device}")
    
    # Create test synthetic camera frame
    dummy_frame = np.random.randint(0, 255, (imgsz[1], imgsz[0], 3), dtype=np.uint8)
    
    # Warmup
    _ = detector.detect_frame(dummy_frame)
    
    times = []
    mem_before = get_process_memory_mb()
    
    for i in range(num_frames):
        t0 = time.perf_counter()
        results = detector.detect_frame(dummy_frame)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        times.append(elapsed_ms)

    mem_after = get_process_memory_mb()
    avg_inference_ms = sum(times) / len(times)
    min_inference_ms = min(times)
    max_inference_ms = max(times)
    fps = 1000.0 / avg_inference_ms if avg_inference_ms > 0 else 0.0

    print(f"Inference Time Avg: {avg_inference_ms:.2f} ms (Min: {min_inference_ms:.2f} ms, Max: {max_inference_ms:.2f} ms)")
    print(f"Max Achievable Inference FPS: {fps:.2f} FPS")
    print(f"Memory Usage: {mem_after:.2f} MB (Delta: {mem_after - mem_before:+.2f} MB)")
    
    return {
        "device": device,
        "avg_inference_ms": avg_inference_ms,
        "fps": fps,
        "memory_mb": mem_after,
    }


def benchmark_live_camera_worker(camera_code="CAM-AMD-ITX-01", stream_url="https://live.corp8.cloud/live/stream/13/index.m3u8", duration_sec=8.0):
    print(f"\n--- 2. End-to-End Live Stream Pipeline Benchmark ({camera_code}) ---")
    cfg = StreamConfigRequest(
        camera_id=camera_code,
        source_url=stream_url,
        sample_fps=5.0,
        confidence_threshold=0.30,
    )
    worker = CameraStreamWorker(cfg)
    worker.start()
    
    print(f"Ingesting live camera stream for {duration_sec} seconds...")
    start_t = time.time()
    time.sleep(duration_sec)
    
    # Capture telemetry metrics
    input_fps = worker.stream_fps
    ai_fps = worker.ai_processed_fps
    latency_ms = worker.latency_ms
    frames_read = worker.total_frames_read
    inferences = worker.total_inferences
    tracks_count = len(worker.tracker.tracks) if worker.tracker else 0
    device = worker.device
    mem_mb = get_process_memory_mb()
    
    worker.stop()
    
    print(f"Results for {camera_code}:")
    print(f" -> Input Stream FPS: {input_fps:.2f} FPS (Total frames decoded: {frames_read})")
    print(f" -> AI Processed FPS: {ai_fps:.2f} FPS (Total inferences executed: {inferences})")
    print(f" -> Approximate Latency: {latency_ms:.2f} ms")
    print(f" -> Active Tracks: {tracks_count}")
    print(f" -> Device: {device}")
    print(f" -> Process Memory: {mem_mb:.2f} MB")
    
    return {
        "camera_id": camera_code,
        "input_fps": input_fps,
        "ai_fps": ai_fps,
        "latency_ms": latency_ms,
        "frames_read": frames_read,
        "inferences": inferences,
        "active_tracks": tracks_count,
        "device": device,
        "memory_mb": mem_mb,
    }


if __name__ == "__main__":
    print("=== STARTING CCTV AI PIPELINE PERFORMANCE MEASUREMENT ===")
    raw_res = benchmark_raw_inference(num_frames=15)
    live_res = benchmark_live_camera_worker(duration_sec=7.0)
    print("\n=== MEASUREMENT COMPLETE ===")
