"""
YOLO26 Utility Functions
========================
Authoritative bounding box formatting, class normalization, and image preprocessing.
"""
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import numpy as np

# Canonical Indian Traffic Classes (Phase 1):
# CAR, AUTO_RICKSHAW, MOTORCYCLE, SCOOTER, BUS, TRUCK, LCV_TEMPO, BICYCLE, PERSON
CANONICAL_CLASSES: Set[str] = {
    "CAR",
    "AUTO_RICKSHAW",
    "MOTORCYCLE",
    "SCOOTER",
    "BUS",
    "TRUCK",
    "LCV_TEMPO",
    "BICYCLE",
    "PERSON",
}

COCO_TO_PHANTOM_CLASSES: Dict[Union[int, str], str] = {
    0: "PERSON",
    "person": "PERSON",
    "pedestrian": "PERSON",
    "human": "PERSON",
    1: "BICYCLE",
    "bicycle": "BICYCLE",
    "cycle": "BICYCLE",
    "pedal_cycle": "BICYCLE",
    2: "CAR",
    "car": "CAR",
    "sedan": "CAR",
    "suv": "CAR",
    "hatchback": "CAR",
    "taxi": "CAR",
    "cab": "CAR",
    3: "MOTORCYCLE",
    "motorcycle": "MOTORCYCLE",
    "motorbike": "MOTORCYCLE",
    "bike": "MOTORCYCLE",
    "moto": "MOTORCYCLE",
    "splendor": "MOTORCYCLE",
    "scooter": "SCOOTER",
    "activa": "SCOOTER",
    "two_wheeler": "MOTORCYCLE",
    "two-wheeler": "MOTORCYCLE",
    5: "BUS",
    "bus": "BUS",
    "minibus": "BUS",
    "transit_bus": "BUS",
    7: "TRUCK",
    "truck": "TRUCK",
    "lorry": "TRUCK",
    "heavy_truck": "TRUCK",
    "pickup": "LCV_TEMPO",
    "lcv": "LCV_TEMPO",
    "tempo": "LCV_TEMPO",
    "lcv_tempo": "LCV_TEMPO",
    "tata_ace": "LCV_TEMPO",
    "van": "CAR",
    "auto_rickshaw": "AUTO_RICKSHAW",
    "autorickshaw": "AUTO_RICKSHAW",
    "auto": "AUTO_RICKSHAW",
    "rickshaw": "AUTO_RICKSHAW",
    "tuk_tuk": "AUTO_RICKSHAW",
    "tuktuk": "AUTO_RICKSHAW",
    "three_wheeler": "AUTO_RICKSHAW",
    "license_plate": "LICENSE_PLATE",
    "licence_plate": "LICENSE_PLATE",
    "plate": "LICENSE_PLATE",
}


def normalize_class_name(raw_name: Union[int, str]) -> str:
    """
    Authoritative class normalization into canonical PHANTOM classes.
    Never returns ambiguous aliases (like bike, taxi, activa, splendor).
    """
    if isinstance(raw_name, int) or (isinstance(raw_name, str) and str(raw_name).isdigit()):
        return COCO_TO_PHANTOM_CLASSES.get(int(raw_name), "CAR")
    
    token = str(raw_name).strip().lower().replace("-", "_").replace(" ", "_")
    return COCO_TO_PHANTOM_CLASSES.get(token, token.upper())


def format_bounding_box(xyxy: List[float], width: Optional[int] = None, height: Optional[int] = None) -> Dict[str, float]:
    x1, y1, x2, y2 = [float(v) for v in xyxy]
    if width and height:
        x1 = max(0.0, min(float(width), x1))
        y1 = max(0.0, min(float(height), y1))
        x2 = max(0.0, min(float(width), x2))
        y2 = max(0.0, min(float(height), y2))
    return {
        "x1": round(x1, 2),
        "y1": round(y1, 2),
        "x2": round(x2, 2),
        "y2": round(y2, 2),
        "width": round(abs(x2 - x1), 2),
        "height": round(abs(y2 - y1), 2),
    }


def preprocess_image(image_input: Any) -> Optional[np.ndarray]:
    if image_input is None:
        return None
    if isinstance(image_input, np.ndarray):
        return image_input
    if hasattr(image_input, "read"):
        import cv2
        data = image_input.read()
        nparr = np.frombuffer(data, np.uint8)
        return cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return None
