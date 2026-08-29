"""
PHANTOM AI Engine Root Package
Exposes YOLO26 detection, tracking, model loading, and stream processing services.
"""
from app.ai.yolo26 import (
    BoundingBox,
    DetectedObject,
    DetectionBatchResult,
    DetectionSummary,
    Track,
    TrackedVehicleState,
    VehicleAttributeExtractor,
    VehicleAttributes,
    YOLO26Config,
    YOLO26Detector,
    YOLO26ModelLoader,
    YOLO26StreamProcessor,
    YOLO26Tracker,
    format_bounding_box,
    get_detector,
    get_model_loader,
    normalize_class_name,
    preprocess_image,
)

__all__ = [
    "YOLO26Config",
    "YOLO26Detector",
    "YOLO26ModelLoader",
    "YOLO26StreamProcessor",
    "YOLO26Tracker",
    "Track",
    "get_detector",
    "get_model_loader",
    "normalize_class_name",
    "format_bounding_box",
    "preprocess_image",
    "VehicleAttributeExtractor",
    "BoundingBox",
    "DetectedObject",
    "VehicleAttributes",
    "DetectionBatchResult",
    "DetectionSummary",
    "TrackedVehicleState",
]
