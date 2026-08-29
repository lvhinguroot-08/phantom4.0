"""
PHANTOM Video Intelligence // YOLO26 AI Inference Module
Central public API for YOLO26 Object Detection, Tracking, and Stream Processing.
"""
from .config import YOLO26Config
from .detector import YOLO26Detector, get_detector
from .model_loader import YOLO26ModelLoader, get_model_loader
from .schemas import (
    BoundingBox,
    DetectedObject,
    DetectionBatchResult,
    DetectionSummary,
    TrackedVehicleState,
    VehicleAttributes,
)
from .stream_processor import YOLO26StreamProcessor
from .tracker import Track, YOLO26Tracker
from .utils import format_bounding_box, normalize_class_name, preprocess_image
from .vehicle_attributes import VehicleAttributeExtractor

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
