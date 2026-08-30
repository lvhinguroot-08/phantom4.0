"""
End-to-End Automated Integration Test Suite for PHANTOM 2.0
Tests:
1. YOLO Object Detection Pipeline
2. ANPR License Plate Localization & OCR Pipeline
3. Combined YOLO + ANPR Asynchronous Video Intelligence Processing
"""
import base64
import json
import os
from pathlib import Path
import time
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ai.anpr.normalize import extract_plate_structure, looks_like_indian_plate, normalize_plate_text
from app.ai.anpr.ocr import build_ocr_processor
from app.ai.yolo26.detector import get_detector
from app.services.video_ai_service import ProcessingMode, video_ai_service

client = TestClient(app)


def test_01_yolo_object_detection():
    """Test 1: YOLO Pipeline on photographic image."""
    detector = get_detector()
    assert detector.is_loaded is True, "YOLO model failed to load."

    # Test on bus.jpg
    sample_path = Path("bus.jpg")
    assert sample_path.exists(), "bus.jpg sample required for testing."

    img = cv2.imread(str(sample_path))
    assert img is not None, "Failed to load test image."

    dets = detector.detect_frame(img, confidence_threshold=0.25)
    assert len(dets) > 0, "YOLO returned zero detections."

    classes_found = {d["class_name"].lower() for d in dets}
    print(f"YOLO detected {len(dets)} objects: {classes_found}")
    assert "person" in classes_found or "bus" in classes_found, "Expected person or bus in test image."

    for d in dets:
        assert "bbox" in d
        assert "confidence" in d
        assert 0.0 <= d["confidence"] <= 1.0


def test_02_anpr_plate_localization_and_ocr():
    """Test 2: ANPR OCR Pipeline and Gujarat RTO Normalization."""
    ocr = build_ocr_processor()

    # Create synthetic high-contrast Gujarat plate
    plate_img = np.full((80, 260, 3), 255, dtype=np.uint8)
    cv2.rectangle(plate_img, (2, 2), (258, 78), (0, 0, 0), 2)
    cv2.rectangle(plate_img, (2, 2), (32, 78), (180, 50, 0), -1) # IND strip
    cv2.putText(plate_img, "GJ05AB1234", (40, 52), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 3)

    ocr_res = ocr.read_text(plate_img)
    norm = normalize_plate_text(ocr_res.raw_text or ocr_res.normalized_text)
    assert "GJ05AB1234" in norm or norm == "GJ05AB1234", f"Unexpected OCR normalization: {norm}"

    struct = extract_plate_structure(norm)
    assert struct["is_gujarat"] is True
    assert struct["state_code"] == "GJ"
    assert struct["rto_code"] == "05"
    assert struct["rto_jurisdiction"] == "Surat"
    print(f"ANPR successfully verified: Plate={norm}, RTO={struct['rto_jurisdiction']}")


def test_03_yolo_anpr_combined_video_processing():
    """Test 3: Full End-to-End YOLO + ANPR Asynchronous Video Processing."""
    video_path = Path("backend/sample_assets/sample_traffic_cctv.mp4")
    if not video_path.exists():
        video_path = Path("sample_assets/sample_traffic_cctv.mp4")
    if not video_path.exists():
        video_path = Path(__file__).resolve().parent.parent.parent / "sample_assets" / "sample_traffic_cctv.mp4"
    assert video_path.exists(), f"Sample test video not found at {video_path}"


    # Submit job via API
    with open(video_path, "rb") as vf:
        response = client.post(
            "/api/process",
            files={"file": ("test_clip.mp4", vf, "video/mp4")},
            data={
                "mode": "yolo_anpr",
                "sample_fps": "5.0",
                "confidence_threshold": "0.25",
                "camera_id": "TEST_JUNCTION_01",
            },
        )

    assert response.status_code == 202, f"Expected 202, got {response.status_code}: {response.text}"
    job_data = response.json()
    job_id = job_data["job_id"]
    assert job_id is not None

    # Poll status until completed
    max_wait_seconds = 30
    start = time.time()
    final_state = None

    while time.time() - start < max_wait_seconds:
        status_res = client.get(f"/api/results/{job_id}")
        assert status_res.status_code == 200
        state = status_res.json()
        if state["status"] in ("COMPLETED", "FAILED", "CANCELLED"):
            final_state = state
            break
        time.sleep(0.5)

    assert final_state is not None, "Job timed out."
    assert final_state["status"] == "COMPLETED", f"Job failed: {final_state.get('error_message')}"
    assert final_state["frames_processed"] > 0
    assert final_state["total_detections"] > 0
    assert "download_url" in final_state
    print(f"Video AI Job completed: Frames={final_state['frames_processed']}, Detections={final_state['total_detections']}, Plates={final_state['total_plates_recognized']}")

    # Verify video download endpoint
    video_dl_res = client.get(f"/api/results/{job_id}/video")
    assert video_dl_res.status_code == 200
    assert len(video_dl_res.content) > 1000, "Downloaded video file empty or corrupt."
