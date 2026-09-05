"""
YOLO26 Inference & Runtime Configuration
Centralized configuration for YOLO26 Object Detection Engine in PHANTOM.
Supports both YOLO26_* and standard YOLO_* / AI_* environment variable naming conventions.
"""
from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import List, Optional


def _parse_classes_env(env_val: Optional[str], default_classes: List[str]) -> List[str]:
    if not env_val:
        return default_classes
    items = [c.strip().upper() for c in env_val.split(",") if c.strip()]
    return items if items else default_classes


@dataclass
class YOLO26Config:
    """Runtime configuration for YOLO26 Object Detection Service."""
    model_name: str = "YOLO26"
    model_version: str = "26.0.0"

    # Model Weights Path: checks YOLO_MODEL_PATH -> YOLO26_MODEL_PATH -> AI_MODEL_PATH -> default
    model_path: str = field(default_factory=lambda: (
        os.getenv("YOLO_MODEL_PATH")
        or os.getenv("YOLO26_MODEL_PATH")
        or os.getenv("AI_MODEL_PATH")
        or str(Path(__file__).resolve().parent / "models" / "yolo26.pt")
    ))

    fallback_baseline_path: str = field(default_factory=lambda: (
        os.getenv("YOLO_BASELINE_PATH", "yolov8n.pt")
    ))

    # Compute Device: auto, cpu, cuda, cuda:0
    device: str = field(default_factory=lambda: (
        os.getenv("YOLO_DEVICE")
        or os.getenv("YOLO26_DEVICE")
        or os.getenv("AI_DEVICE")
        or "auto"
    ))

    # Detection Confidence Threshold
    confidence_threshold: float = field(default_factory=lambda: float(
        os.getenv("YOLO_CONFIDENCE")
        or os.getenv("YOLO26_CONFIDENCE_THRESHOLD")
        or os.getenv("AI_CONFIDENCE_THRESHOLD")
        or "0.35"
    ))

    iou_threshold: float = field(default_factory=lambda: float(
        os.getenv("YOLO_IOU_THRESHOLD")
        or os.getenv("YOLO26_IOU_THRESHOLD")
        or os.getenv("AI_IOU_THRESHOLD")
        or "0.45"
    ))

    input_size: int = field(default_factory=lambda: int(
        os.getenv("YOLO_INPUT_SIZE")
        or os.getenv("YOLO26_INPUT_SIZE")
        or "640"
    ))

    half_precision: bool = field(default_factory=lambda: (
        (os.getenv("YOLO_HALF") or os.getenv("YOLO26_HALF") or "false").lower() in ("true", "1")
    ))

    primary_classes: List[str] = field(default_factory=lambda: [
        "PERSON",
        "CAR",
    ])

    target_classes: List[str] = field(default_factory=lambda: _parse_classes_env(
        os.getenv("YOLO_TARGET_CLASSES") or os.getenv("YOLO26_TARGET_CLASSES"),
        [
            "CAR",
            "AUTO_RICKSHAW",
            "MOTORCYCLE",
            "SCOOTER",
            "BUS",
            "TRUCK",
            "LCV_TEMPO",
            "BICYCLE",
            "PERSON",
            "LICENSE_PLATE",
        ],
    ))

    enable_tracking: bool = field(default_factory=lambda: (
        (os.getenv("YOLO_ENABLE_TRACKING") or os.getenv("YOLO26_ENABLE_TRACKING") or "true").lower() in ("true", "1")
    ))

    # ByteTrack Configuration (Phase 1)
    track_high_thresh: float = field(default_factory=lambda: float(
        os.getenv("YOLO_TRACK_HIGH_THRESH", "0.50")
    ))
    track_low_thresh: float = field(default_factory=lambda: float(
        os.getenv("YOLO_TRACK_LOW_THRESH", "0.15")
    ))
    track_buffer: int = field(default_factory=lambda: int(
        os.getenv("YOLO_TRACK_BUFFER", "30")
    ))
    match_thresh: float = field(default_factory=lambda: float(
        os.getenv("YOLO_MATCH_THRESH", "0.70")
    ))

    sample_fps: float = field(default_factory=lambda: float(
        os.getenv("YOLO_INFERENCE_FPS")
        or os.getenv("YOLO26_SAMPLE_FPS")
        or os.getenv("AI_FRAME_INTERVAL_FPS")
        or "2.0"
    ))

    # Phase 2 Traffic Violation & Helmet Configuration
    helmet_model_path: Optional[str] = field(default_factory=lambda: (
        os.getenv("HELMET_MODEL_PATH")
        or os.getenv("YOLO_HELMET_MODEL_PATH")
    ))
    helmet_min_confidence: float = field(default_factory=lambda: float(
        os.getenv("HELMET_MIN_CONFIDENCE", "0.55")
    ))
    no_helmet_confirmation_window: int = field(default_factory=lambda: int(
        os.getenv("NO_HELMET_CONFIRMATION_WINDOW", "5")
    ))
    triple_riding_confirmation_window: int = field(default_factory=lambda: int(
        os.getenv("TRIPLE_RIDING_CONFIRMATION_WINDOW", "5")
    ))
    min_association_confidence: float = field(default_factory=lambda: float(
        os.getenv("MIN_ASSOCIATION_CONFIDENCE", "0.45")
    ))
    track_min_age: int = field(default_factory=lambda: int(
        os.getenv("TRACK_MIN_AGE", "3")
    ))
    violation_cooldown_seconds: int = field(default_factory=lambda: int(
        os.getenv("VIOLATION_COOLDOWN_SECONDS", "60")
    ))
    evidence_output_dir: str = field(default_factory=lambda: (
        os.getenv("EVIDENCE_OUTPUT_DIR", "static/evidence")
    ))

    # Phase 3 ANPR & License Plate Intelligence Configuration
    plate_model_path: Optional[str] = field(default_factory=lambda: (
        os.getenv("PLATE_MODEL_PATH")
        or os.getenv("YOLO_PLATE_MODEL_PATH")
        or os.getenv("ANPR_MODEL_PATH")
    ))
    anpr_min_ocr_confidence: float = field(default_factory=lambda: float(
        os.getenv("ANPR_MIN_OCR_CONFIDENCE", "0.50")
    ))
    anpr_temporal_window: int = field(default_factory=lambda: int(
        os.getenv("ANPR_TEMPORAL_WINDOW", "8")
    ))
    anpr_min_confirmations: int = field(default_factory=lambda: int(
        os.getenv("ANPR_MIN_CONFIRMATIONS", "3")
    ))
    anpr_cooldown_seconds: int = field(default_factory=lambda: int(
        os.getenv("ANPR_COOLDOWN_SECONDS", "60")
    ))
    enable_perspective_correction: bool = field(default_factory=lambda: (
        (os.getenv("ANPR_ENABLE_PERSPECTIVE", "true")).lower() in ("true", "1")
    ))

    demo_fallback_enabled: bool = True


