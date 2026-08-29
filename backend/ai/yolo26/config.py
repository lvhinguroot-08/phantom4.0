"""
YOLO26 Inference Configuration
State-of-the-art detector configuration for PHANTOM Video Intelligence Platform.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
import os


@dataclass
class YOLO26Config:
    """Runtime configuration for YOLO26 Object Detection Service."""
    model_name: str = "YOLO26"
    model_version: str = "26.0.0"
    model_path: str = os.getenv(
        "YOLO26_MODEL_PATH",
        str(Path(__file__).parent / "models" / "yolo26.pt")
    )
    
    # Detection thresholds
    confidence_threshold: float = float(os.getenv("YOLO26_CONFIDENCE_THRESHOLD", "0.35"))
    iou_threshold: float = float(os.getenv("YOLO26_IOU_THRESHOLD", "0.45"))
    input_size: int = int(os.getenv("YOLO26_INPUT_SIZE", "640"))
    
    # Hardware compute device (CPU fallback active by default)
    device: str = os.getenv("YOLO26_DEVICE", "cpu")
    half_precision: bool = os.getenv("YOLO26_HALF", "false").lower() in ("true", "1")
    
    # Target classes for surveillance & law enforcement
    target_classes: List[str] = field(default_factory=lambda: [
        "PERSON",
        "CAR",
        "TRUCK",
        "BUS",
        "MOTORCYCLE",
        "BICYCLE",
        "OTHER_VEHICLE",
        "LICENSE_PLATE",
    ])
    
    demo_fallback_enabled: bool = True
