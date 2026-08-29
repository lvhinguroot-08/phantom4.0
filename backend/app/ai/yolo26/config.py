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
            "PERSON",
            "CAR",
            "MOTORCYCLE",
            "BUS",
            "TRUCK",
            "BICYCLE",
            "OTHER_VEHICLE",
            "LICENSE_PLATE",
        ],
    ))

    enable_tracking: bool = field(default_factory=lambda: (
        (os.getenv("YOLO_ENABLE_TRACKING") or os.getenv("YOLO26_ENABLE_TRACKING") or "true").lower() in ("true", "1")
    ))

    sample_fps: float = field(default_factory=lambda: float(
        os.getenv("YOLO_INFERENCE_FPS")
        or os.getenv("YOLO26_SAMPLE_FPS")
        or os.getenv("AI_FRAME_INTERVAL_FPS")
        or "2.0"
    ))

    demo_fallback_enabled: bool = True
