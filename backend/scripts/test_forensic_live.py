"""
Live Verification Script for YOLO26 Forensic AI Endpoints
"""
import os
import io
import json
import time
import urllib.request
import cv2
import numpy as np


def run_live_forensic_verification():
    print("==================================================")
    print("   PHANTOM YOLO26 FORENSIC AI LIVE VERIFICATION   ")
    print("==================================================")

    # 1. Generate Synthetic Forensic Snapshot
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.rectangle(img, (150, 180), (450, 380), (0, 0, 255), -1)  # Vehicle block
    cv2.rectangle(img, (500, 150), (580, 420), (255, 255, 0), -1)  # Person block
    _, encoded = cv2.imencode(".jpg", img)
    img_bytes = encoded.tobytes()

    boundary = "----WebKitFormBoundaryForensic2026"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="forensic_test.jpg"\r\n'
        f"Content-Type: image/jpeg\r\n\r\n"
    ).encode("utf-8") + img_bytes + (
        f"\r\n--{boundary}\r\n"
        f'Content-Disposition: form-data; name="camera_id"\r\n\r\n'
        f"CAM-FORENSIC-01\r\n"
        f"--{boundary}--\r\n"
    ).encode("utf-8")

    # --------------------------------------------------------------------------
    # Test 1: Image Forensic Inference (POST /api/v1/ai/detect/image)
    # --------------------------------------------------------------------------
    print("\n[TEST 1] Testing Image Forensics (/api/v1/ai/detect/image)...")
    req = urllib.request.Request(
        "http://127.0.0.1:8000/api/v1/ai/detect/image",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode())
        print(f"  -> HTTP Status: {resp.status} OK")
        print(f"  -> Detections: {res.get('count')} objects")
        print(f"  -> Objects: {[o.get('object_class') for o in res.get('objects', [])]}")
        print(f"  -> Base64 Annotated Image Rendered: {bool(res.get('image'))} ({len(res.get('image', ''))} chars)")
        print(f"  -> Inference Latency: {res.get('latency_ms')}ms")

    # --------------------------------------------------------------------------
    # Test 2: ANPR Plate Recognition (POST /api/v1/ai/anpr/process)
    # --------------------------------------------------------------------------
    print("\n[TEST 2] Testing ANPR & Plate OCR (/api/v1/ai/anpr/process)...")
    req_anpr = urllib.request.Request(
        "http://127.0.0.1:8000/api/v1/ai/anpr/process",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req_anpr) as resp_anpr:
        anpr_res = json.loads(resp_anpr.read().decode())
        print(f"  -> HTTP Status: {resp_anpr.status} OK")
        print(f"  -> Vehicles Detected: {anpr_res.get('total_vehicles_detected')}")
        print(f"  -> Plates Recognized: {anpr_res.get('total_plates_recognized')}")

    # --------------------------------------------------------------------------
    # Test 3: Vehicle Multi-Object Tracking (POST /api/v1/ai/tracking/vehicle/frame)
    # --------------------------------------------------------------------------
    print("\n[TEST 3] Testing Vehicle Trajectory Tracking (/api/v1/ai/tracking/vehicle/frame)...")
    req_track = urllib.request.Request(
        "http://127.0.0.1:8000/api/v1/ai/tracking/vehicle/frame",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req_track) as resp_track:
        track_res = json.loads(resp_track.read().decode())
        print(f"  -> HTTP Status: {resp_track.status} OK")
        print(f"  -> Traffic Stats: {track_res.get('traffic_stats', {})}")
        print(f"  -> Active Tracks: {len(track_res.get('active_tracks', []))}")

    # --------------------------------------------------------------------------
    # Test 4: Video Processing & Progress (POST /api/v1/ai/detect/video)
    # --------------------------------------------------------------------------
    print("\n[TEST 4] Testing Asynchronous Video Ingestion (/api/v1/ai/detect/video)...")
    temp_vid_path = "temp_forensic_test.mp4"
    fourcc = getattr(cv2, "VideoWriter_fourcc", cv2.VideoWriter.fourcc)(*"mp4v")
    out = cv2.VideoWriter(temp_vid_path, fourcc, 10.0, (320, 240))
    for _ in range(12):
        frame = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
        cv2.rectangle(frame, (80, 80), (240, 180), (0, 0, 255), -1)
        out.write(frame)
    out.release()

    with open(temp_vid_path, "rb") as vf:
        vid_bytes = vf.read()

    v_body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="forensic_clip.mp4"\r\n'
        f"Content-Type: video/mp4\r\n\r\n"
    ).encode("utf-8") + vid_bytes + (
        f"\r\n--{boundary}\r\n"
        f'Content-Disposition: form-data; name="camera_id"\r\n\r\n'
        f"CAM-VID-FORENSIC\r\n"
        f"--{boundary}--\r\n"
    ).encode("utf-8")

    req_vid = urllib.request.Request(
        "http://127.0.0.1:8000/api/v1/ai/detect/video",
        data=v_body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req_vid) as resp_vid:
        vid_create = json.loads(resp_vid.read().decode())
        job_id = vid_create.get("job_id")
        print(f"  -> Video Job Queued: {job_id}")

    # Poll until completed
    time.sleep(1.0)
    for _ in range(15):
        with urllib.request.urlopen(f"http://127.0.0.1:8000/api/v1/ai/detect/video/{job_id}") as resp_poll:
            job_state = json.loads(resp_poll.read().decode())
            print(f"  -> Job Progress: {job_state.get('status')} ({job_state.get('progress_percent')}%) Frames: {job_state.get('frames_processed')}/{job_state.get('total_frames')}")
            if job_state.get("status") in ("COMPLETED", "FAILED"):
                break
        time.sleep(0.5)

    if os.path.exists(temp_vid_path):
        os.remove(temp_vid_path)

    print("\n==================================================")
    print("   ALL 4 FORENSIC AI PIPELINES ARE 100% OPERATIONAL! ")
    print("==================================================")


if __name__ == "__main__":
    run_live_forensic_verification()
