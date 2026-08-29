"""
PHANTOM Video Intelligence // YOLO26 AI Inference Module
Aliases app.ai.yolo26 to maintain single source of truth.
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
