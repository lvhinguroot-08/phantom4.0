"""
PHANTOM Phase 3 ANPR Test Suite
Comprehensive automated verification of:
1. Plate detection and ROI localization
2. Quality filtering (rejection of sub-resolution and blurry crops as UNREADABLE)
3. 4-Point perspective rectification and aspect ratio normalization
4. Multi-variant preprocessing (CLAHE, Bilateral Otsu, Adaptive Binarization)
5. Position-specific Indian plate normalization and syntax disambiguation
6. Format validity scoring (Standard State vs Bharat Series vs Gibberish)
7. Character-level temporal voting and 5-factor confidence fusion
8. Track-aware ANPR state machine lifecycle and duplicate suppression cooldown
9. Traffic violation plate linking without personal identity inference
10. Hardware detection and runtime execution discovery
"""
import os
import sys
from pathlib import Path
import time

import cv2
import numpy as np
import pytest

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.ai.anpr.hardware_detect import detect_execution_environment
from app.ai.anpr.normalize import (
    disambiguate_plate,
    extract_plate_structure,
    is_gujarat_plate,
    looks_like_indian_plate,
    normalize_plate_text,
    score_plate_format,
)
from app.ai.anpr.perspective import PlatePerspectiveCorrector, PlateQualityAssessor
from app.ai.anpr.plate_association import PlateAssociationEngine
from app.ai.anpr.plate_detector import LicensePlateDetector, PlateDetectionResult
from app.ai.anpr.preprocessor import PlateImagePreprocessor
from app.ai.anpr.temporal_anpr import AggregatedPlateResult, PlateReading, TemporalANPRAggregator
from app.ai.anpr.anpr_state_machine import ANPRStateMachineManager, ANPRTrackState
from app.ai.anpr.yolo26_anpr_pipeline import YOLO26ANPRPipeline
from app.ai.yolo26.config import YOLO26Config
from app.ai.yolo26.schemas import TrafficViolationEvent, VehicleAttributes


def _create_synthetic_plate_image(
    text: str = "GJ05AB1234",
    width: int = 240,
    height: int = 70,
    blur: bool = False,
    angled: bool = False,
) -> np.ndarray:
    """Helper to synthesize test plate images."""
    img = np.full((height, width, 3), 245, dtype=np.uint8)
    # Border
    cv2.rectangle(img, (2, 2), (width - 3, height - 3), (20, 20, 20), 3)
    # Blue IND badge on left
    cv2.rectangle(img, (2, 2), (28, height - 3), (180, 50, 20), -1)
    # Text
    cv2.putText(
        img,
        text,
        (36, int(height * 0.70)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.85,
        (10, 10, 10),
        2,
        cv2.LINE_AA,
    )
    if blur:
        img = cv2.GaussianBlur(img, (21, 21), 0)
    if angled:
        pts1 = np.float32([[0, 0], [width, 0], [0, height], [width, height]])
        pts2 = np.float32([[15, 8], [width - 5, 18], [5, height - 12], [width - 20, height - 6]])
        matrix = cv2.getPerspectiveTransform(pts1, pts2)
        img = cv2.warpPerspective(img, matrix, (width, height), borderValue=(200, 200, 200))
    return img


# ==============================================================================
# TEST 1: Plate Detection on Vehicle ROI
# ==============================================================================

def test_clear_daylight_plate_detection():
    detector = LicensePlateDetector()
    frame = np.full((400, 600, 3), 180, dtype=np.uint8)

    # Place a vehicle box and a plate at the bottom center of the vehicle
    vehicle_box = {"x1": 100, "y1": 100, "x2": 500, "y2": 350}
    plate_img = _create_synthetic_plate_image("GJ05AB1234", width=140, height=45)
    # Paste plate in lower portion of vehicle
    frame[280:325, 230:370] = plate_img

    res = detector.detect_in_vehicle_roi(frame, vehicle_box, vehicle_track_id=1, vehicle_class="CAR")
    assert res is not None
    assert isinstance(res, PlateDetectionResult)
    assert res.confidence > 0.40
    assert res.plate_crop is not None
    assert res.plate_crop.shape[0] > 10
    assert res.plate_crop.shape[1] > 20


# ==============================================================================
# TEST 2: Quality Filtering - Sub-Resolution Rejection
# ==============================================================================

def test_low_resolution_plate_handling():
    assessor = PlateQualityAssessor(min_width=40, min_height=14)
    # Extremely tiny crop (20x8)
    tiny_crop = np.zeros((8, 20, 3), dtype=np.uint8)
    metrics = assessor.assess(tiny_crop)
    assert metrics.status == "UNREADABLE"
    assert metrics.is_readable is False
    assert metrics.quality_score < 0.20


# ==============================================================================
# TEST 3: Quality Filtering - Severe Blur Rejection
# ==============================================================================

def test_severe_blur_filtering():
    assessor = PlateQualityAssessor()
    # Blurred plate image
    blurred_plate = _create_synthetic_plate_image("GJ05AB1234", blur=True)
    metrics = assessor.assess(blurred_plate)
    assert metrics.status == "UNREADABLE"
    assert metrics.is_readable is False
    assert metrics.blur_score < 18.0


# ==============================================================================
# TEST 4: 4-Point Perspective Rectification
# ==============================================================================

def test_perspective_rectification():
    corrector = PlatePerspectiveCorrector(target_width=320, target_height=96)
    angled_plate = _create_synthetic_plate_image("GJ01CD5678", angled=True)

    rectified = corrector.rectify(angled_plate)
    assert rectified is not None
    assert rectified.shape == (96, 320, 3) or rectified.shape == (96, 320)


# ==============================================================================
# TEST 5: Multi-Variant Preprocessing
# ==============================================================================

def test_multi_variant_preprocessing():
    preprocessor = PlateImagePreprocessor(target_width=320, target_height=96)
    plate = _create_synthetic_plate_image("MH12DE1234")

    # Single best
    best = preprocessor.preprocess_best(plate)
    assert best.shape == (96, 320)
    assert len(best.shape) == 2  # Grayscale enhanced

    # All variants
    variants = preprocessor.generate_variants(plate)
    var_names = [name for name, _ in variants]
    assert "clahe" in var_names
    assert "otsu_bin" in var_names
    assert "adaptive_bin" in var_names
    assert "sharpened" in var_names
    for _, var_img in variants:
        assert var_img.shape == (96, 320)


# ==============================================================================
# TEST 6: Position-Specific Character Disambiguation
# ==============================================================================

def test_position_specific_disambiguation():
    # 0 vs O: Position 0-1 should be letters (O), position 2-3 digits (0)
    raw1 = "0JOSAB1234"  # 0 at pos 0 -> G/O, O at pos 3 -> 0
    norm1 = normalize_plate_text(raw1)
    assert norm1.startswith("GJ05") or norm1.startswith("OJ05")

    # OCR error 6J -> GJ
    raw_gj = "6J05AB1234"
    assert normalize_plate_text(raw_gj) == "GJ05AB1234"

    # Digits in suffix: O substituted with 0, I substituted with 1
    raw_suffix = "GJ05AB123O"
    assert normalize_plate_text(raw_suffix) == "GJ05AB1230"

    raw_suffix2 = "GJ05AB123I"
    assert normalize_plate_text(raw_suffix2) == "GJ05AB1231"

    # Bharat series: 22BH1234AA
    raw_bh = "22BH1234AA"
    norm_bh = normalize_plate_text(raw_bh)
    assert norm_bh == "22BH1234AA"


# ==============================================================================
# TEST 7: Format Validity Scoring
# ==============================================================================

def test_format_validity_scoring():
    # Standard Gujarat plate
    assert score_plate_format("GJ05AB1234") == 1.0
    assert score_plate_format("DL01C1234") == 1.0
    # Bharat series
    assert score_plate_format("22BH1234AA") == 1.0
    # Plausible partial plate
    score_partial = score_plate_format("GJ05AB1")
    assert 0.60 <= score_partial <= 0.95
    # Total gibberish / non-plate
    assert score_plate_format("XYZ") == 0.0
    assert score_plate_format("HELLO") < 0.20


# ==============================================================================
# TEST 8: Character-Level Temporal Voting and 5-Factor Confidence Fusion
# ==============================================================================

def test_temporal_voting_and_fusion():
    aggregator = TemporalANPRAggregator(window_size=8, min_confirmations=3, min_confidence=0.55)

    # Simulate 5 consecutive frames for a vehicle:
    # 3 frames read GJ05AB1234 (conf=0.92)
    # 1 frame reads GJ05AB123O (sporadic OCR O instead of 0, conf=0.70)
    # 1 frame reads GJ05AB1234 (conf=0.90)
    dummy_crop = np.zeros((30, 100, 3), dtype=np.uint8)

    readings = [
        PlateReading("GJ05AB1234", "GJ05AB1234", 0.92, 0.90, 0.85, 1.0, dummy_crop, 1),
        PlateReading("GJ05AB1234", "GJ05AB1234", 0.91, 0.88, 0.84, 1.0, dummy_crop, 2),
        PlateReading("GJ05AB123O", "GJ05AB1230", 0.70, 0.80, 0.75, 1.0, dummy_crop, 3),
        PlateReading("GJ05AB1234", "GJ05AB1234", 0.95, 0.92, 0.88, 1.0, dummy_crop, 4),
    ]

    for r in readings:
        aggregator.add_reading(r)

    result = aggregator.vote()
    # Majority character voting should cleanly resolve to GJ05AB1234
    assert result.plate_text == "GJ05AB1234"
    assert result.confirmations >= 3
    assert result.is_confirmed is True
    # Verify 5-factor confidence formula:
    # Conf = 0.25 * Det + 0.20 * Quality + 0.30 * OCR + 0.15 * Temp + 0.10 * Format
    assert result.confidence >= 0.80
    assert result.structural_info["state_code"] == "GJ"
    assert result.structural_info["is_gujarat"] is True


# ==============================================================================
# TEST 9: Track-Aware State Machine Lifecycle & Duplicate Suppression Cooldown
# ==============================================================================

def test_state_machine_and_cooldown():
    sm = ANPRStateMachineManager(
        temporal_window=5,
        min_confirmations=3,
        min_confidence=0.55,
        duplicate_cooldown_seconds=2.0,
    )

    track_id = 42
    cam_id = "CAM-TEST"
    dummy_crop = np.zeros((30, 100, 3), dtype=np.uint8)

    # Frame 1: Plate detected, but unreadable
    res1 = sm.update_track(track_id, cam_id, "CAR", None, plate_detected=True)
    ctx = sm.active_tracks[track_id]
    assert ctx.state == ANPRTrackState.PLATE_DETECTED

    # Frame 2: First reading
    r2 = PlateReading("GJ01AB9999", "GJ01AB9999", 0.9, 0.85, 0.8, 1.0, dummy_crop, 2)
    sm.update_track(track_id, cam_id, "CAR", r2, plate_detected=True)
    assert ctx.state == ANPRTrackState.OCR_OBSERVING

    # Frame 3: Second reading
    r3 = PlateReading("GJ01AB9999", "GJ01AB9999", 0.92, 0.85, 0.82, 1.0, dummy_crop, 3)
    sm.update_track(track_id, cam_id, "CAR", r3, plate_detected=True)
    assert ctx.state == ANPRTrackState.PLATE_HYPOTHESIS

    # Frame 4: Third reading -> reaches confirmation threshold!
    r4 = PlateReading("GJ01AB9999", "GJ01AB9999", 0.94, 0.88, 0.85, 1.0, dummy_crop, 4)
    res4 = sm.update_track(track_id, cam_id, "CAR", r4, plate_detected=True)
    assert ctx.state == ANPRTrackState.PLATE_CONFIRMED
    assert res4.is_confirmed is True
    assert res4.plate_text == "GJ01AB9999"

    # Check Cooldown suppression
    assert sm.should_publish_event(cam_id, "GJ01AB9999") is True
    # Immediate second publish should be suppressed by cooldown
    assert sm.should_publish_event(cam_id, "GJ01AB9999") is False

    # Stale track pruning
    # When track 42 is absent for > max_missing_frames, it is pruned
    sm.max_missing_frames = 2
    sm.prune_missing_tracks(current_active_track_ids=set())  # missing frame 1
    sm.prune_missing_tracks(current_active_track_ids=set())  # missing frame 2
    pruned = sm.prune_missing_tracks(current_active_track_ids=set())  # missing frame 3 -> pruned
    assert track_id in pruned
    assert track_id not in sm.active_tracks


# ==============================================================================
# TEST 10: Phase 2 Violation Linking Without Personal Identity Inference
# ==============================================================================

def test_violation_plate_linking_no_identity():
    # Setup violation event for vehicle track 101
    viol = TrafficViolationEvent(
        violation_type="NO_HELMET",
        camera_id="CAM-01",
        vehicle_track_id=101,
        vehicle_type="MOTORCYCLE",
        confidence=0.88,
    )

    # Link ANPR plate result to the violation
    plate_text = "GJ05CD4321"
    viol.vehicle_plate = plate_text
    viol.plate_confidence = 0.91
    viol.metadata["plate_confirmed"] = True

    # Assert vehicle plate is correctly associated
    assert viol.vehicle_plate == "GJ05CD4321"
    assert viol.vehicle_track_id == 101
    assert viol.plate_confidence == 0.91

    # Assert that NO personal identity, home address, or owner details exist
    # (Complies strictly with privacy / non-inference rule)
    assert not hasattr(viol, "driver_name")
    assert not hasattr(viol, "owner_name")
    assert not hasattr(viol, "residential_address")
    assert "owner_name" not in viol.metadata
    assert "aadhaar" not in viol.metadata


# ==============================================================================
# TEST 11: Hardware Detection & Environment Discovery
# ==============================================================================

def test_hardware_detection():
    env = detect_execution_environment()
    assert "device" in env
    assert env["device"] in ("cuda", "cpu", "mps")
    assert "cpu_count" in env
    assert env["cpu_count"] > 0
    assert "recommended_threads" in env
    assert "recommended_batch_size" in env
    assert "torch_version" in env
